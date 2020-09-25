import numpy as np
import cv2
import datetime
import multiprocessing
import signal
import time
import sys
import pyzed.sl as sl

class ZEDRecorder(multiprocessing.Process):
    def __init__(self, pauseEvent, stopEvent, resolution=sl.RESOLUTION.HD720, framerate=30, dir=""):
        super(ZEDRecorder, self).__init__()
        self.initParams = sl.InitParameters()
        self.initParams.camera_resolution = sl.RESOLUTION.HD720
        self.initParams.depth_mode = sl.DEPTH_MODE.NONE
        self.initParams.camera_fps = framerate

        self.dir = dir
        self.pauseEvent = pauseEvent
        self.stopEvent = stopEvent

    def run(self):
        now = datetime.datetime.now()
        filename = now.strftime("ZED_%Y-%m-%d-%H-%M-%S")+".svo"
        print("ZED Camera - recording to " + filename)

        cam = sl.Camera()
        stauts = cam.open(self.initParams)
        if status != sl.ERROR_CODE.SUCCESS:
            print(repr(status))
        else:
            recording_param = sl.RecordingParameters(filename, sl.SVO_COMPRESSION_MODE.H264)
            err = cam.enable_recording(recording_param)
            if err != sl.ERROR_CODE.SUCCESS:
                print(repr(status))
            else:
                runtime = sl.RuntimeParameters()
                while not self.stopEvent.is_set():
                    if not self.pauseEvent.is_set():
                        cam.grab(runtime)
                cam.disable_recording()
                cam.close()
                print("Stopped recording!")