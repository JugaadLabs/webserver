import numpy as np
import cv2
import datetime
import multiprocessing
import signal
import time
import sys
import pyzed.sl as sl
import os

class ZEDRecorder(multiprocessing.Process):
    def __init__(self, pauseEvent, stopEvent, zedParams={
    "resolution": sl.RESOLUTION.HD720, "depth": sl.DEPTH_MODE.PERFORMANCE, "framerate": 30, "dir": ""}):
        super(ZEDRecorder, self).__init__()
        self.initParams = sl.InitParameters()
        self.initParams.camera_resolution = zedParams['resolution']
        self.initParams.depth_mode = zedParams['depth']
        self.initParams.camera_fps = zedParams['framerate']

        self.dir = zedParams['dir']
        self.pauseEvent = pauseEvent
        self.stopEvent = stopEvent

    def run(self):
        now = datetime.datetime.now()
        filepath = os.path.join(self.dir, now.strftime("ZED_%Y-%m-%d-%H-%M-%S")+".svo")
        print("ZED Camera - recording to " + filepath)

        cam = sl.Camera()
        status = cam.open(self.initParams)
        if status != sl.ERROR_CODE.SUCCESS:
            print(repr(status))
            self.stopEvent.set()
        else:
            recording_param = sl.RecordingParameters(filepath, sl.SVO_COMPRESSION_MODE.H264)
            err = cam.enable_recording(recording_param)
            if err != sl.ERROR_CODE.SUCCESS:
                print(repr(status))
                self.stopEvent.set()
            else:
                runtime = sl.RuntimeParameters()
                frames_recorded = 0
                while not self.stopEvent.is_set():
                    if not self.pauseEvent.is_set():
                        frames_recorded += 1
                        print("Frame count ZED: " + str(frames_recorded), end="\r")
                        cam.grab(runtime)
                    else:
                        time.sleep(0.1)
                print("ZED Final count - " + str(frames_recorded))
                cam.disable_recording()
                cam.close()
                print("Stopped recording!")