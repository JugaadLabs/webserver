# Zirui Zang
# 20201010

import numpy as np
import cv2
from time import perf_counter
import time
import os

from src.uilts.tensorrt_uilts import get_engine, allocate_buffers, do_inference
from src.uilts.image import transform_preds, iou
from src.uilts.uilts import coco_class_name, color_list, detection_class_name_8cls
from scipy.optimize import least_squares

class monoDistance():
    def __init__(self, image_size, bird_view_size, trt_engine_path, class_names, cls_index_list, H, L0, calibrationDir, debug = 0):
        self.trt_engine_path = trt_engine_path
        self.class_names = class_names
        self.cls_index_list = cls_index_list
        self.image_size = image_size
        down_ratio = 4
        self.det_size = [image_size[0]//down_ratio, image_size[1]//down_ratio]
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.matching_row = np.zeros((0, 12))
        self.matched_bboxs = np.zeros((0, 6))
        self.object_ids = list(range(1, 100))
        self.debug = debug

        # Mechanical Parameters:
        self.H = 1.96133177 # height of mounting
        self.f_x = 322.40 # focal length
        self.f_y = 323.30
        self.l_0 = 0.36680308 # distance of bottom image edge to camera when tilted
        self.calibrationDir = calibrationDir

        engine = get_engine(trt_engine_path, fp16_mode=True)
        self.context = engine.create_execution_context()
        self.inputs, self.outputs, self.bindings, self.stream = allocate_buffers(engine)
        self.blank_birds_view_img = self.blank_birds_view(bird_view_size)

    def detect_object(self, img):
        img_x = cv2.resize(img, self.image_size)
        x = img_x.transpose(2, 0, 1).reshape(
            1, 3, self.image_size[1], self.image_size[0]).astype(np.float32)
        self.inputs[0].host = x.reshape(-1)
        outs = do_inference(self.context, bindings=self.bindings,
                                    inputs=self.inputs, outputs=self.outputs, stream=self.stream)
        dets = outs[0].reshape([1, 100, 6])
        return dets

    def post_process(self, dets, image, vis_thresh, nms_iou_thresh = 0.5, box_area_thresh = 500):
        dets = dets.reshape(1, -1, dets.shape[2])
        h, w = image.shape[0:2]
        c = np.array([w / 2, h / 2], dtype=np.float32)
        s = np.array([w, h], dtype=np.float32)
        dets[0, :, :2] = transform_preds(dets[0, :, 0:2], c, s, self.det_size)
        dets[0, :, 2:4] = transform_preds(dets[0, :, 2:4], c, s, self.det_size)

        selected_bboxs = np.zeros((0, 6))
        for j in self.cls_index_list:
            top_preds = dets[0, (dets[0, :, 5] == j), :6].astype(np.float32) # find box in this class
            top_preds = top_preds[(top_preds[:, 4] > vis_thresh[j]), :6].astype(np.float32) # find box passing the threshold
            top_preds = top_preds[np.argsort(top_preds[:, 4])[::-1], :] # sort with confidence
            while top_preds.shape[0] > 0: # non-maximum suppression
                box_max_conf = top_preds[0, :]
                box_area = (box_max_conf[2] - box_max_conf[0] + 1) * (box_max_conf[3] - box_max_conf[1] + 1)
                if box_area < box_area_thresh: # area thresholding
                    top_preds = np.delete(top_preds, 0, axis=0)
                    continue
                selected_bboxs = np.vstack([selected_bboxs, box_max_conf])
                top_preds = np.delete(top_preds, 0, axis=0)
                if top_preds.shape[0] > 0:
                    iou_list = []
                    for ind in range(0, top_preds.shape[0]):
                        iou_list.append(iou(box_max_conf, top_preds[ind, 0:4]))
                    iou_list = np.array(iou_list)
                    top_preds = top_preds[(iou_list < nms_iou_thresh), :]

        return selected_bboxs
    
    def calcualte_distance(self, bbox):
        
        H = self.H # height of mounting
        f_x = self.f_x # focal length
        f_y = self.f_y
        l_0 = self.l_0 # distance of bottom image edge to camera when tilted

        input_w = self.image_size[0]
        input_h = self.image_size[1]
          
        y_pixel = bbox[2] - input_h / 2
        beta = np.arctan(H / l_0) - np.arctan(input_h / 2 / f_y)
        alpha = beta + np.arctan(y_pixel / f_y)
        # print(np.rad2deg(beta)) # beta is the angle between optical axis and ground
        l_y = H / np.tan(alpha)

        x_pixel = bbox[0] - input_w / 2
        l_x = l_y * x_pixel / (f_x - y_pixel * np.sin(beta) * f_y / f_x)

        return [l_x, l_y]

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
        if self.debug == 0:
            lines = [5, 10, 15, 20]
        else:
            lines = [5, 10, 15, 20, 25]
        
        birds_view_img = np.ones((img_size, img_size, 3), np.uint8)
        birds_view_img = birds_view_img * 255
        self.horizontal_fov = 75
        self.distance_factor = int((img_size / 2) / np.sin(np.deg2rad(self.horizontal_fov / 2))* 1.15 / lines[-1]) 
        
        boundary_color = (200, 200, 200)
        boundary_thickness = 2
        birds_view_img = cv2.line(birds_view_img, (0, int((img_size/2)/np.tan(np.deg2rad(180-self.horizontal_fov)/2))), 
                                  (int(img_size/2), img_size), boundary_color, boundary_thickness)
        birds_view_img = cv2.line(birds_view_img, (img_size, int((img_size/2)/np.tan(np.deg2rad(180-self.horizontal_fov)/2))), 
                                  (int(img_size/2), img_size), boundary_color, boundary_thickness)
        
        for dis_text in lines:
            textsize = cv2.getTextSize('{} m'.format(dis_text), self.font, img_size/1000, 1)[0]
            cv2.putText(birds_view_img, '{} m'.format(dis_text), (int((img_size-textsize[0])/2), int(img_size - self.distance_factor*dis_text -textsize[1])), self.font,
                            img_size/1000, (0, 0, 0), thickness=1, lineType=cv2.LINE_AA)     
            draw_half_circle_rounded(birds_view_img, self.distance_factor, dis_text, boundary_color, boundary_thickness, self.horizontal_fov)   
                    
        return birds_view_img

    def birds_view(self, birds_view_img, selected_bboxs, bbox_distances):
        height, width = birds_view_img.shape[0:2]
        def add_object(image, size, center, color, txt, distance):
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
            
            arrow_length = 5
            arrow_aim = (int(center[0] + distance[2] * arrow_length), int(center[1] - distance[3] * arrow_length))
            cv2.arrowedLine(image, center, arrow_aim, color, thickness = 1, tipLength = 0.5)

        for ind, bbox in enumerate(selected_bboxs):
            distance = bbox_distances[ind]
            if distance[1] > 0 and time.time()-distance[4] < 0.1:
                horizontal_line = distance[1] * np.tan(np.deg2rad(self.horizontal_fov / 2)) * 2 * self.distance_factor
                size = (bbox[2] - bbox[0]) / birds_view_img.shape[1] * horizontal_line
                center = distance * self.distance_factor
                center = (distance[0] * self.distance_factor + width / 2, height - distance[1] * self.distance_factor)

                conf = bbox[4]
                bbox = np.array(bbox, dtype=np.int32)
                cat = bbox[5]
                if cat == 0:
                    color = color_list[cat+1].tolist()
                    if self.debug == 0:
                        txt = '({:.1f} {:.1f})m ({:.1f} {:.1f})m/s'.format(distance[0], distance[1], distance[2], distance[3])
                    else:
                        txt = 'ID:{} {} {:.1f} ({:.1f}, {:.1f})m'.format(int(distance[5]), self.class_names[cat], conf, distance[0], distance[1])
                    add_object(birds_view_img, size, center, color, txt, distance)

    def add_det_label(self, img, bboxs, distances, calib = False):
        for ind, bbox in enumerate(bboxs):
            if calib or time.time() - distances[ind, 4] < 0.1:
                conf = bbox[4]
                bbox = np.array(bbox, dtype=np.int32)
                cat = bbox[5]
                if cat == 0: # limiting to person for debug
                    color = color_list[cat+1].tolist()
                    if self.debug == 0 and not calib:
                        if distances[ind][1] < 0 or distances[ind][1] > 30:
                            txt = '{} {:.1f} ({:.1f}, far)m'.format(self.class_names[cat], conf, distances[ind][0])
                        else:
                            txt = '{} {:.1f} ({:.1f}, {:.1f})m'.format(self.class_names[cat], conf, distances[ind][0], distances[ind][1])
                    elif not calib:
                        txt = 'ID:{} {:.1f} {:.1f}'.format(int(distances[ind][5]), distances[ind][10], distances[ind][11])

                    if calib: 
                        txt = '{} {:.1f}'.format(self.class_names[cat], conf)
                    cat_size = cv2.getTextSize(txt, self.font, 0.5, 2)[0]
                    cv2.rectangle(img, (bbox[0], bbox[1]),
                                (bbox[2], bbox[3]), color, 2)
                    cv2.rectangle(img, (bbox[0], bbox[3]-2 - cat_size[1]),
                                (bbox[0] + cat_size[0], bbox[3]-2), color, -1)
                    cv2.putText(img, txt, (bbox[0], bbox[3]-2), self.font,
                                0.5, (0, 0, 0), thickness=1, lineType=cv2.LINE_AA)

    def tracking(self, selected_bboxs, match_thresh = 0.5, time_thresh = 0.5, occlusion_thresh = 8):
        ## Structure of self.matching_row
        ## self.matching_row[match_ind, 0:4] = [pos_x, pos_y, vel_x, vel_y]
        ## self.matching_row[match_ind, 4:6] = [time, object_id]
        ## self.matching_row[match_ind, 6:12] = [bbox_x_center, bbox_y_top, bbox_y_down, class, bbox_ratio, bbox_width]
        
        bbox_track_xy = np.transpose([(selected_bboxs[:, 2] + selected_bboxs[:, 0]) / 2, selected_bboxs[:, 1], selected_bboxs[:, 3], \
                                       selected_bboxs[:, 5], (selected_bboxs[:, 3] - selected_bboxs[:, 1])/(selected_bboxs[:, 2] - selected_bboxs[:, 0]), (selected_bboxs[:, 2] - selected_bboxs[:, 0])])
        # print('bbox_track_xy', bbox_track_xy.shape)

        if len(self.matching_row) > 0:
            # clean up outdated objects
            delete_list = np.where(time.time() - self.matching_row[:, 4] > time_thresh)[0]
            for ind in delete_list[::-1]:
                self.object_ids.append(self.matching_row[ind, 5])
            self.matching_row = np.delete(self.matching_row, delete_list, axis=0)
            self.matched_bboxs = np.delete(self.matched_bboxs, delete_list, axis=0)

            # find matches
            for match_ind, match in enumerate(self.matching_row):
                occlusion_flag = False
                if len(bbox_track_xy) > 0:
                    distances_top = np.sqrt((bbox_track_xy[:, 0] - match[6]) ** 2 + (bbox_track_xy[:, 1] - match[7]) ** 2)
                    distances_down = np.sqrt((bbox_track_xy[:, 0] - match[6]) ** 2 + (bbox_track_xy[:, 2] - match[8]) ** 2)
                    min_distance_ind = np.argmin(distances_down)
                    distances = distances_down
                    
                    if distances[min_distance_ind] > self.matching_row[match_ind, 11] * match_thresh:
                        min_distance_ind = np.argmin(distances_top)
                        distances = distances_top            
            
                    if distances[min_distance_ind] < self.matching_row[match_ind, 11] * match_thresh and bbox_track_xy[min_distance_ind, 3] == self.matching_row[match_ind, 9]:
                        delta_time = time.time() - self.matching_row[match_ind, 4]

                        if self.matching_row[match_ind, 9] == 0 and bbox_track_xy[min_distance_ind, 4] < 2.4 and bbox_track_xy[min_distance_ind, 5] < 80:
                            # if we see a far person's aspect ratio is not regular, we will use the width of bbox to estimate distance
                            print('id', self.matching_row[match_ind, 5])
                            print(bbox_track_xy[min_distance_ind, 2])
                            bbox_track_xy[min_distance_ind, 2] = bbox_track_xy[min_distance_ind, 1] + bbox_track_xy[min_distance_ind, 5] * 2.8
                            print(bbox_track_xy[min_distance_ind, 2])
                        
                        track_xy = self.calcualte_distance(bbox_track_xy[min_distance_ind, :])
                        self.matching_row[match_ind, 2] = (track_xy[0] - self.matching_row[match_ind, 0]) / delta_time
                        self.matching_row[match_ind, 3] = (track_xy[1] - self.matching_row[match_ind, 1]) / delta_time
                        self.matching_row[match_ind, 0] = track_xy[0].copy()
                        self.matching_row[match_ind, 1] = track_xy[1].copy()
                        self.matching_row[match_ind, 4] = time.time()
                        # self.matching_row[match_ind, 5] id is not changed
                        self.matching_row[match_ind, 6:] = bbox_track_xy[min_distance_ind, :]
                        self.matched_bboxs[match_ind] = selected_bboxs[min_distance_ind, :]
                        bbox_track_xy = np.delete(bbox_track_xy, min_distance_ind, axis=0)
                        selected_bboxs = np.delete(selected_bboxs, min_distance_ind, axis=0)
                else:
                    break

        # save unmatched as new objects
        if len(bbox_track_xy) > 0:
            for xy_ind, bbox_track_xy_element in enumerate(bbox_track_xy):
                if len(self.object_ids) > 0:
                    track_xy = self.calcualte_distance(bbox_track_xy_element)
                    row_temp = np.zeros(self.matching_row.shape[1])
                    row_temp[:6] = [track_xy[0].copy(), track_xy[1].copy(), 0, 0, time.time(), self.object_ids.pop(0)]
                    row_temp[6:] = bbox_track_xy_element.copy()
                    self.matching_row = np.vstack((self.matching_row, row_temp))
                    self.matched_bboxs = np.vstack((self.matched_bboxs, selected_bboxs[xy_ind])) 

        # print('')
        # print('self.matching_row', self.matching_row.shape)
        # print('self.matching_row', self.matching_row)
        # print('self.matched_bboxs', self.matched_bboxs.shape)
        # print('self.matched_bboxs', self.matched_bboxs)
        return self.matched_bboxs, self.matching_row
        
    def detection_birdsview(self, img, vis_thresh, nms_iou_thresh, box_area_thresh):
        
        dets = self.detect_object(img)
        selected_bboxs = self.post_process(dets, img, vis_thresh, nms_iou_thresh, box_area_thresh)
        selected_bboxs, bbox_distances = self.tracking(selected_bboxs)

        self.add_det_label(img, selected_bboxs, bbox_distances)
        birds_view_img = self.blank_birds_view_img.copy()
        self.birds_view(birds_view_img, selected_bboxs, bbox_distances)

        return img, birds_view_img, selected_bboxs, bbox_distances

    def detection(self, img, vis_thresh, nms_iou_thresh, box_area_thresh):
        
        dets = self.detect_object(img)
        selected_bboxs = self.post_process(dets, img, vis_thresh, nms_iou_thresh, box_area_thresh)
        self.add_det_label(img, selected_bboxs, None, calib = True)

        return img, selected_bboxs

    def distance_calibration(self, img_paths, distances, minimum_visible_distance, 
                            vis_thresh, nms_iou_thresh, box_area_thresh, x0 = [2.0, 0.4]):

        calibration_error = 0
        pixel_pos = []
        for ind in range(len(distances)):
            img_input = cv2.imread(img_paths[ind])
            img, selected_bboxs = self.detection(img_input, vis_thresh, nms_iou_thresh, box_area_thresh)
            # FIXME: Use the actual path
            cv2.imwrite(os.path.join(self.calibrationDir, 'calib_det_' + str(ind) + '.jpg'), img)
            calibration_error = -ind

            if selected_bboxs.shape[0] > 0:
                for obj_ind in range(selected_bboxs.shape[0]):
                    center_x = (selected_bboxs[0, 0] + selected_bboxs[0, 2]) / 2
                    print(center_x)
                    if center_x < 280 and center_x > 200:
                        pixel_pos.append(selected_bboxs[0, 3])
                        calibration_error = 0
                        break
                calibration_error = 0 if calibration_error == 0 else -ind
            else:
                print('Person at {} m is not detected.'.format(distances[ind]))

        def distance_model(x, t, y):
            H = x[0]
            l_0 = x[1]
            input_h = 640
            f_y = 323.30
            print(x,t,y)
            return H / np.tan( np.arctan(H / l_0) - np.arctan(input_h/2/f_y) + np.arctan((t - input_h / 2)/f_y)) - y - l_0

        t_train = np.array(pixel_pos)
        y_train = np.array(distances) - minimum_visible_distance
        print('t_train', t_train)
        print('y_train', y_train)

        if calibration_error == 0 and t_train.shape == y_train.shape:
            res_robust = least_squares(distance_model, x0, loss='soft_l1', f_scale=0.1, args=(t_train, y_train))
            print(res_robust.x)
            if np.abs(res_robust.x[0] - x0[0]) > 0.3 or np.abs(res_robust.x[1] - x0[1]) > 0.2:
                calibration_error = 1
            else:
                self.H = res_robust.x[0]
                self.l_0 = res_robust.x[1]

        return calibration_error, self.H, self.l_0



