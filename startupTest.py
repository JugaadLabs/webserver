import cv2
import netifaces as ni
from pathlib import Path
import os
import signal
import sys
import string
import subprocess
import time
import traceback
import threading
import multiprocessing
import datetime
import cherrypy
from settings import params
import fileinput
from tqdm import tqdm
import re
import shutil
from src.CSIStreamer import CSIStreamer
from src.DetectionHandler import DetectionHandler

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


def zedTest(dir):
    zedFrameLock = None
    zedStreamer = None
    if ZED_ENABLED:
        zedFrameLock = threading.Lock()
        zedStreamer = ZEDStreamer(zedFrameLock, dir, params["zedStreamer"]["recordingInterval"], params["zedStreamer"]
                                  ["resolution"], params["zedStreamer"]["depth"], params["zedStreamer"]["framerate"])
        zedStreamThread = threading.Thread(
            None, zedStreamer.run, daemon=True)
        zedStreamThread.start()
    time.sleep(5)
    print("ZED Test")
    zedStreamer.startRecording(datetime.datetime.now())
    for i in tqdm(range(10)):
        time.sleep(1)
    zedStreamer.stopRecording()
    zedStreamer.terminateEvent.set()


detectionsReceived = 0


def detectionReceiver(detectionDict):
    global detectionsReceived
    detectionsReceived += 1
    assert('img' in detectionDict)
    assert('birdsView' in detectionDict)
    assert('selectedBboxes' in detectionDict)
    assert('bboxDistances' in detectionDict)


def results(dir):
    global detectionsReceived
    print("Results\n=========")
    files = os.listdir(dir)
    r = re.compile('.*avi')
    aviFiles = list(filter(r.match, files))
    r = re.compile('.*svo')
    svoFiles = list(filter(r.match, files))
    r = re.compile('.*pkl')
    pklFiles = list(filter(r.match, files))
    svoTest = False
    zedTest = False
    if ZED_ENABLED:
        zedTest = True
        if (len(svoFiles)>0):
            svoTest = True
    camTest = True if (len(aviFiles) > 0 and len(pklFiles) > 0) else False
    detectionTest = True if detectionsReceived > 0 else False

    print("ZED Detected: %s\nSVO File Created: %s\nCamera Test: %s\nObject Detector Test: %s" % (zedTest, svoTest, camTest, detectionTest))
    if zedTest and svoTest and camTest and detectionTest:
        print("All tests passed! The webserver should be able to run with full functionality enabled.")
def startupTest(dir='test'):
    zedTest(dir)

    csiDevice, _ = selfTest()

    csiFrameLock = threading.Lock()
    csiStreamer = CSIStreamer(csiFrameLock, dir, params["csiStreamer"]["recordingInterval"], csiDevice, params["csiStreamer"]
                              ["stdResolution"], params["csiStreamer"]["hdResolution"], params["csiStreamer"]["recordingResolution"], params["csiStreamer"]["framerate"])
    time.sleep(5)
    print("CSI Test")
    csiStreamer.startRecording(0)
    for i in tqdm(range(10)):
        time.sleep(1)
    csiStreamer.stopRecording()

    DetectionHandler(
        dir, params["detectionHandler"]["framerate"], params["detectionHandler"]["recordingResolution"], params["detectionHandler"]["enginepath"], params["detectionHandler"]["H"], params["detectionHandler"]["L0"])
    print("Waiting for object detector to come online...")
    time.sleep(20)
    cherrypy.engine.subscribe('debugDetections', detectionReceiver)
    for i in tqdm(range(10)):
        time.sleep(1)
    print("Total detections: "+str(detectionsReceived))

def main():
    dir = './test'
    dir = os.path.abspath(dir)
    Path(dir).mkdir(parents=True, exist_ok=True)
    startupTest(dir)
    results(dir)
    os.kill(os.getpid(), signal.SIGQUIT)

if __name__ == "__main__":
    main()
