from src.trig_distance import monoDistance
from src.uilts.uilts import detection_class_name_3cls
import numpy as np
import multiprocessing
import sys

def detectionProcessFunction(enginePath, sendQueue, recvQueue):
    inputResolution = (480, 640)
    birdsEyeResolution = 480
    vis_thresh = 0.35
    nms_iou_thresh = 0.5
    box_area_thresh = 500
    monoDist = monoDistance(
        inputResolution, birdsEyeResolution, enginePath, detection_class_name_3cls, np.array(range(3)))
    print("Running Object Detector Process!")
    vis_thresh = [0.35, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]
    nms_iou_thresh = 0.3
    box_area_thresh = 300
    minimum_visible_distance = 0.1
    distances = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    while True:
        while not recvQueue.empty():
            data = recvQueue.get()
            if type(data) is list:
                error, H, l0 = monoDist.distance_calibration(data, distances, minimum_visible_distance, vis_thresh, nms_iou_thresh, box_area_thresh)
                sendQueue.put([error, H, l0])
            elif type(data) is np.ndarray:
                img = data
                processedImg, birds_view_img, selected_bboxs, bbox_distances = monoDist.detection_birdsview(
                    img, vis_thresh, nms_iou_thresh, box_area_thresh)
                dataDict = {
                    "img": processedImg,
                    "birdsView": birds_view_img,
                    "selectedBboxes": selected_bboxs,
                    "bboxDistances": bbox_distances
                }
                sendQueue.put(dataDict)
