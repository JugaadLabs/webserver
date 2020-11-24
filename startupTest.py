import cv2
import netifaces as ni
from pathlib import Path
import os
import sys
import string
import subprocess
import time
import traceback
import threading
import multiprocessing

from settings import params
import fileinput
from tqdm import tqdm

from src.FilesHandler import FilesHandler
from src.RecordingHandler import RecordingHandler
from src.BarcodeHandler import BarcodeHandler
from src.TestHandler import TestHandler
from src.CSIStreamer import CSIStreamer
from src.DocuHandler import DocuHandler
from src.WebSocketHandler import WebSocketHandler
from src.DetectionHandler import DetectionHandler
from src.DisabledHandler import DisabledHandler

ZED_ENABLED = True
try:
    import pyzed.sl as sl
except ImportError as e:
    ZED_ENABLED = False
else:
    from src.ZEDStreamer import ZEDStreamer


def testCamera(camId):
    cap = cv2.VideoCapture(camId)
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if w == 0 or h == 0 or w/h > 3:
        return -1
    cap.release()
    return camId


def selfTest():
    ret0 = testCamera(0)
    ret1 = testCamera(1)

    csi = max(ret0, ret1)

    zed = False
    if ZED_ENABLED:
        cam = sl.Camera()
        status = cam.open()
        if status == sl.ERROR_CODE.SUCCESS:
            cam.close()
            zed = True
    return csi, zed


def startupTest(dir='.'):
    dir = os.path.abspath(dir)
    Path(dir).mkdir(parents=True, exist_ok=True)

    zedStatus = False
    csiDevice, zedStatus = selfTest()

    csiStatus = True if csiDevice != -1 else False

    csiFrameLock = threading.Lock()
    csiStreamer = CSIStreamer(csiFrameLock, dir, params["csiStreamer"]["recordingInterval"], csiDevice, params["csiStreamer"]
                              ["stdResolution"], params["csiStreamer"]["hdResolution"], params["csiStreamer"]["recordingResolution"], params["csiStreamer"]["framerate"])

    zedFrameLock = None
    zedStreamer = None
    if ZED_ENABLED:
        zedFrameLock = threading.Lock()
        zedStreamer = ZEDStreamer(zedFrameLock, dir, params["zedStreamer"]["recordingInterval"], params["zedStreamer"]
                                  ["resolution"], params["zedStreamer"]["depth"], params["zedStreamer"]["framerate"])
        zedStreamThread = threading.Thread(
            None, zedStreamer.run, daemon=True)
        zedStreamThread.start()

    RecordingHandler(
        dir, csiStreamer, zedStreamer, csiStatus, zedStatus, 0, params["recordingHandler"]["previewResolution"], params["recordingHandler"]["zedPreviewResolution"])
    BarcodeHandler(dir, params["barcodeHandler"]["crop"], params["barcodeHandler"]["timeout"],
                   params["barcodeHandler"]["previewResolution"], params["barcodeHandler"]["recordingResolution"])
    DetectionHandler(
        dir, params["detectionHandler"]["framerate"], params["detectionHandler"]["recordingResolution"], params["detectionHandler"]["enginepath"], params["detectionHandler"]["H"], params["detectionHandler"]["L0"])
    FilesHandler(dir)
    TestHandler()
    DocuHandler()

    csiStreamer.startRecording(0)
    for i in tqdm(range(10)):
        time.sleep(1)
    csiStreamer.stopRecording()


def main():
    startupTest()

if __name__ == "__main__":
    main()
