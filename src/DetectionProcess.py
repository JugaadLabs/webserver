from src.trig_distance import monoDistance
from src.uilts.uilts import detection_class_name_3cls
import numpy as np
import zmq
from src.zmq_utils import zmqNode
import sys


def main():
    inputResolution = (480, 640)
    birdsEyeResolution = 480
    vis_thresh = 0.35
    nms_iou_thresh = 0.5
    box_area_thresh = 500
    enginePath = "/home/nvidia/engine/forklift_68fds_3cls_1.trt"
    if len(sys.argv) > 1:
        enginePath = sys.argv[1]
    monoDist = monoDistance(
        inputResolution, birdsEyeResolution, enginePath, detection_class_name_3cls, np.array(range(3)))

    try:
        receiveImgNode = zmqNode('recv', 9500)
        sendResultsNode = zmqNode('send', 9501)
    except zmq.error.ZMQError:
        print("Detection Process already running")
        return
    else:
        while True:
            try:
                img = receiveImgNode.recv_array()
            except zmq.error.Again as e:
                pass
            else:
                img, birds_view_img, selected_bboxs, bbox_distances = monoDist.detection_birdsview(
                    img, vis_thresh, nms_iou_thresh, box_area_thresh)
                dataDict = {
                    "img": img,
                    "birdsView": birds_view_img,
                    "selectedBboxes": selected_bboxs,
                    "bboxDistances": bbox_distances
                }
                sendResultsNode.send_zipped_pickle(dataDict)


if __name__ == "__main__":
    main()
