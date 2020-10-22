# Zirui Zang
# 20201010

import numpy as np
import cv2
from time import perf_counter

from src.uilts.tensorrt_uilts import get_engine, allocate_buffers, do_inference
from src.uilts.image import transform_preds, iou
from src.uilts.uilts import coco_class_name, color_list, detection_class_name_3cls

class monoDistance():
    def __init__(self, image_size, bird_view_size, trt_engine_path, class_names, cls_index_list):
        self.trt_engine_path = trt_engine_path
        self.class_names = class_names
        self.cls_index_list = cls_index_list
        self.image_size = image_size
        down_ratio = 4
        self.det_size = [image_size[0]//down_ratio, image_size[1]//down_ratio]
        self.font = cv2.FONT_HERSHEY_SIMPLEX

        self.engine = get_engine(trt_engine_path, fp16_mode=True)
        self.inputs, self.outputs, self.bindings, self.stream = allocate_buffers(self.engine)
        self.blank_birds_view_img = self.blank_birds_view(bird_view_size)

    def detect_object(self, img):
        img_x = cv2.resize(img, self.image_size)
        x = img_x.transpose(2, 0, 1).reshape(
            1, 3, self.image_size[1], self.image_size[0]).astype(np.float32)
        self.inputs[0].host = x.reshape(-1)
        outs = do_inference(self.engine, bindings=self.bindings,
                                    inputs=self.inputs, outputs=self.outputs, stream=self.stream)
        dets = outs[0].reshape([1, 100, 6])
        return dets

    def post_process(self, dets, image, vis_thresh = 0.4, nms_iou_thresh = 0.5, box_area_thresh = 500):
        dets = dets.reshape(1, -1, dets.shape[2])
        h, w = image.shape[0:2]
        c = np.array([w / 2, h / 2], dtype=np.float32)
        s = np.array([w, h], dtype=np.float32)
        dets[0, :, :2] = transform_preds(dets[0, :, 0:2], c, s, self.det_size)
        dets[0, :, 2:4] = transform_preds(dets[0, :, 2:4], c, s, self.det_size)

        selected_bboxs = []
        for j in self.cls_index_list:
            top_preds = dets[0, (dets[0, :, 5] == j), :6].astype(np.float32) # find box in this class
            top_preds = top_preds[(top_preds[:, 4] > vis_thresh), :6].astype(np.float32) # find box passing the threshold
            top_preds = top_preds[np.argsort(top_preds[:, 4])[::-1], :] # sort with confidence
            while top_preds.shape[0] > 0: # non-maximum suppression
                box_max_conf = top_preds[0, :]
                box_area = (box_max_conf[2] - box_max_conf[0] + 1) * (box_max_conf[3] - box_max_conf[1] + 1)
                if box_area < box_area_thresh: # area thresholding
                    top_preds = np.delete(top_preds, 0, axis=0)
                    continue
                selected_bboxs.append(box_max_conf)
                top_preds = np.delete(top_preds, 0, axis=0)
                if top_preds.shape[0] > 0:
                    iou_list = []
                    for ind in range(0, top_preds.shape[0]):
                        iou_list.append(iou(box_max_conf, top_preds[ind, 0:4]))
                    iou_list = np.array(iou_list)
                    top_preds = top_preds[(iou_list < nms_iou_thresh), :]

        return np.array(selected_bboxs)

    def add_det_label(self, img, bboxs, distances):
        for ind, bbox in enumerate(bboxs):
            conf = bbox[4]
            bbox = np.array(bbox, dtype=np.int32)
            cat = bbox[5]
            color = color_list[cat+1].tolist()
            txt = '{} {:.1f} ({:.1f}, {:.1f})m'.format(self.class_names[cat], conf, distances[ind][0], distances[ind][1])
            cat_size = cv2.getTextSize(txt, self.font, 0.5, 2)[0]
            cv2.rectangle(img, (bbox[0], bbox[1]),
                        (bbox[2], bbox[3]), color, 2)
            cv2.rectangle(img, (bbox[0], bbox[3]-2 - cat_size[1]),
                        (bbox[0] + cat_size[0], bbox[3]-2), color, -1)
            cv2.putText(img, txt, (bbox[0], bbox[3]-2), self.font,
                        0.5, (0, 0, 0), thickness=1, lineType=cv2.LINE_AA)
    
    def calcualte_distance(self, selected_bboxs):
        bbox_distances = np.zeros((selected_bboxs.shape[0], 2))
        
        H = 2.0 # height of mounting
        f_x = 322.40 # focal length
        f_y = 323.30
        l_0 = 0.15 # distance of bottom image edge to camera when tilted

        input_w = self.image_size[0]
        input_h = self.image_size[1]

        for ind, bbox in enumerate(selected_bboxs):            
            y_pixel = bbox[3] - input_h / 2
            beta = np.arctan(H / l_0) - np.arctan(input_h / 2 / f_y)
            alpha = beta + np.arctan(y_pixel / f_y)
            # print(np.rad2deg(beta))
            l_y = H / np.tan(alpha)

            x_pixel = (bbox[2] + bbox[0]) / 2 - input_w / 2
            l_x = l_y * x_pixel / (f_x - y_pixel * np.sin(beta) * f_y / f_x)

            bbox_distances[ind, 0] = l_x
            bbox_distances[ind, 1] = l_y
        return bbox_distances

    def blank_birds_view(self, img_size):

        def draw_half_circle_rounded(image, distance_factor, distance, boundary_color, boundary_thickness, horizontal_fov):
            height, width = image.shape[0:2]
            # Ellipse parameters
            radius = distance_factor * distance
            center = (int(width / 2), int(height))
            axes = (radius, radius)
            angle = 0
            startAngle = -90 - int(horizontal_fov/2+1)
            endAngle = -90 + int(horizontal_fov/2+1)
            cv2.ellipse(image, center, axes, angle, startAngle, endAngle, boundary_color, boundary_thickness)

        img_size = int(img_size)
        birds_view_img = np.ones((img_size, img_size, 3), np.uint8)
        birds_view_img = birds_view_img * 255
        self.horizontal_fov = 75
        self.distance_factor = int((img_size / 2) / np.sin(np.deg2rad(self.horizontal_fov / 2))* 1.15 / 20) 

        boundary_color = (200, 200, 200)
        boundary_thickness = 2
        birds_view_img = cv2.line(birds_view_img, (0, int((img_size/2)/np.tan(np.deg2rad(180-self.horizontal_fov)/2))), 
                                  (int(img_size/2), img_size), boundary_color, boundary_thickness)
        birds_view_img = cv2.line(birds_view_img, (img_size, int((img_size/2)/np.tan(np.deg2rad(180-self.horizontal_fov)/2))), 
                                  (int(img_size/2), img_size), boundary_color, boundary_thickness)
        
        for dis_text in [5, 10, 15, 20]:
            textsize = cv2.getTextSize('{} m'.format(dis_text), self.font, img_size/1000, 1)[0]
            cv2.putText(birds_view_img, '{} m'.format(dis_text), (int((img_size-textsize[0])/2), int(img_size - self.distance_factor*dis_text -textsize[1])), self.font,
                            img_size/1000, (0, 0, 0), thickness=1, lineType=cv2.LINE_AA)     
            draw_half_circle_rounded(birds_view_img, self.distance_factor, dis_text, boundary_color, boundary_thickness, self.horizontal_fov)   
                    
        return birds_view_img

    def birds_view(self, birds_view_img, selected_bboxs, bbox_distances):
        height, width = birds_view_img.shape[0:2]
        def add_object(image, size, center, color, txt):
            # Ellipse parameters
            radius = int(size)
            center = (int(center[0]), int(center[1]))
            axes = (radius, radius)
            angle = 0
            startAngle = 0
            endAngle = 360
            cv2.ellipse(image, center, axes, angle, startAngle, endAngle, color, thickness = 1)
            cv2.putText(image, txt, center, self.font,
                        0.5, color, thickness=1, lineType=cv2.LINE_AA)

        for ind, bbox in enumerate(selected_bboxs):
            distance = bbox_distances[ind]
            horizontal_line = distance[1] * np.tan(np.deg2rad(self.horizontal_fov / 2)) * 2 * self.distance_factor
            size = (bbox[2] - bbox[0]) / birds_view_img.shape[1] * horizontal_line
            center = distance * self.distance_factor
            center = (distance[0] * self.distance_factor + width / 2, height - distance[1] * self.distance_factor)

            conf = bbox[4]
            bbox = np.array(bbox, dtype=np.int32)
            cat = bbox[5]
            color = color_list[cat+1].tolist()
            # txt = '{} {:.1f}'.format(self.class_names[cat], conf)
            txt = '{} {:.1f} ({:.1f}, {:.1f})m'.format(self.class_names[cat], conf, distance[0], distance[1])

            add_object(birds_view_img, size, center, color, txt)
        
    def detection_birdsview(self, img, vis_thresh, nms_iou_thresh, box_area_thresh):
        
        dets = self.detect_object(img)
        selected_bboxs = self.post_process(dets, img, vis_thresh, nms_iou_thresh, box_area_thresh)
        bbox_distances = self.calcualte_distance(selected_bboxs)
        self.add_det_label(img, selected_bboxs, bbox_distances)
        birds_view_img = self.blank_birds_view_img.copy()
        self.birds_view(birds_view_img, selected_bboxs, bbox_distances)

        return img, birds_view_img, selected_bboxs, bbox_distances


def main():
    # input_w = input_h = 480
    input_w = 480
    input_h = 640
    vis_thresh = 0.35
    nms_iou_thresh = 0.5
    box_area_thresh = 500
    bird_view_size = 480

    use_engine = '68fds'
    # use_engine = '85'
    import_video = False
    save_hud_video = True
    save_bird_video = True
    save_raw_video = False

    if use_engine == '85':
        trt_engine_path = "ctdet_hardnet_85_480x640.trt"
        cls_index_list = np.array([0, 1, 2, 3, 5, 7, 11])
        class_names = coco_class_name
    elif use_engine == '68fds':
        trt_engine_path = "forklift_68fds_3cls_1.trt"
        cls_index_list = np.array(range(3))
        class_names = detection_class_name_3cls

    print('Trigonometry Distance JL')
    cap = cv2.VideoCapture(1)
    if import_video: 
        cap = cv2.VideoCapture('output_raw18.avi')
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, -1)
    cap.set(cv2.CAP_PROP_CONTRAST, 15)
    format_avi = cv2.VideoWriter_fourcc(*'XVID')
    if save_bird_video:
        out_bird = cv2.VideoWriter('output_bird.avi', format_avi, 10, (bird_view_size, bird_view_size))
    if save_hud_video:
        out = cv2.VideoWriter('output.avi', format_avi, 10, (input_w, input_h))
    if save_raw_video:
        out_raw = cv2.VideoWriter('output_raw.avi', format_avi, 10, (input_w, input_h))

    image_size = (input_w, input_h)
    mono_distance = monoDistance(image_size, bird_view_size, trt_engine_path, class_names, cls_index_list)
    # blank_birds_view_img = mono_distance.blank_birds_view(bird_view_size)

    if cap.isOpened() or import_video:
        try:
            while True:
                t = perf_counter()
                ret, img = cap.read()
                img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                if save_raw_video: out_raw.write(img)

                t2 = perf_counter()
                # dets = mono_distance.detect_object(img)
                img, birds_view_img, selected_bboxs, bbox_distances = \
                    mono_distance.detection_birdsview(img, vis_thresh, nms_iou_thresh, box_area_thresh)
                t3 = perf_counter()
                
                # selected_bboxs = mono_distance.post_process(dets, img, vis_thresh, nms_iou_thresh, box_area_thresh)
                # bbox_distances = mono_distance.calcualte_distance(selected_bboxs)
                # mono_distance.add_det_label(img, selected_bboxs, bbox_distances)
                # birds_view_img = blank_birds_view_img.copy()
                # mono_distance.birds_view(birds_view_img, selected_bboxs, bbox_distances)

                cv2.imshow("CSI Camera", img)
                cv2.imshow("Bird's View", birds_view_img)
                print(' Latency = %.2f ms  (net=%.2f ms) FPS=%.2f'%((perf_counter()-t)*1000, (t3-t2)*1000, 1/((perf_counter()-t))))
                if save_hud_video: out.write(img)
                if save_bird_video: out_bird.write(birds_view_img)

                keyCode = cv2.waitKey(1) & 0xFF
                # Stop the program on the ESC key
                if keyCode == 27:
                    break
            cv2.destroyAllWindows()
            cap.release()
        except(KeyboardInterrupt):
            cv2.destroyAllWindows()
            cap.release()
            print('^ _ ^C^')
    else:
        print('Camera not connected')


if __name__ == "__main__":
    main()
