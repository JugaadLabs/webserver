from src.trig_distance import monoDistance
from src.uilts.uilts import detection_class_name_3cls, detection_class_name_8cls
import numpy as np
import multiprocessing
import sys
import os

def detectionProcessFunction(enginePath, terminateEvent, sendQueue, recvQueue, sendListQueue, recvListQueue, H, L0, dir):
    calibrationDir = os.path.join(dir, "calibration")
    inputResolution = (480, 640)
    birdsEyeResolution = 480
    vis_thresh = 0.35
    nms_iou_thresh = 0.5
    box_area_thresh = 500
    monoDist = monoDistance(
        inputResolution, birdsEyeResolution, enginePath, detection_class_name_8cls, np.array(range(8)), H, L0, calibrationDir)
    print("Running Object Detector Process! ", os.getpid())
    vis_thresh = [0.35, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]
    nms_iou_thresh = 0.3
    box_area_thresh = 300
    minimum_visible_distance = 0.1
    distances = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
    while not terminateEvent.is_set():
        if not terminateEvent.is_set() and not recvListQueue.empty():
            data = recvListQueue.get()
            if type(data) is list:
                print("Got a data", data)
                error, H, l0 = monoDist.distance_calibration(data, distances, minimum_visible_distance, vis_thresh, nms_iou_thresh, box_area_thresh)
                if not terminateEvent.is_set():
                    sendListQueue.put([error, H, l0])
        if not terminateEvent.is_set() and not recvQueue.empty():
            data = recvQueue.get()
            if type(data) is np.ndarray:
                img = data
                processedImg, birds_view_img, selected_bboxs, bbox_distances = monoDist.detection_birdsview(
                    img, vis_thresh, nms_iou_thresh, box_area_thresh)
                dataDict = {
                    "img": processedImg,
                    "birdsView": birds_view_img,
                    "selectedBboxes": selected_bboxs,
                    "bboxDistances": bbox_distances
                }
                if not terminateEvent.is_set():
                    sendQueue.put(dataDict)
