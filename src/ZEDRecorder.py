import numpy as np
import cv2
import datetime
import signal
import time
import sys
import pyzed.sl as sl
import os

class ZEDRecorder:
    def __init__(self, pauseEvent, stopEvent, zedParams={
    "resolution": sl.RESOLUTION.HD720, "depth": sl.DEPTH_MODE.PERFORMANCE, "framerate": 15, "dir": "."},
    recording_interval = sys.maxsize):
        self.initParams = sl.InitParameters()
        self.initParams.camera_resolution = zedParams['resolution']
        self.initParams.depth_mode = zedParams['depth']
        self.initParams.camera_fps = zedParams['framerate']

        self.dir = zedParams['dir']
        self.pauseEvent = pauseEvent
        self.stopEvent = stopEvent
        self.recording_interval = recording_interval

    def intializeCamera(self):
        cam = sl.Camera()
        status = cam.open(self.initParams)
        if status != sl.ERROR_CODE.SUCCESS:
            print(repr(status))
            self.stopEvent.set()
            return None
        else:
            now = datetime.datetime.now()
            filepath = os.path.join(self.dir, now.strftime("ZED_%Y-%m-%d-%H-%M-%S")+".svo")
            print("ZED Camera - recording to " + filepath)
            recording_param = sl.RecordingParameters(filepath, sl.SVO_COMPRESSION_MODE.H264)
            err = cam.enable_recording(recording_param)
            if err != sl.ERROR_CODE.SUCCESS:
                print(repr(status))
                self.stopEvent.set()
                return None
        return cam

    def cleanup(self, frames_recorded, cam):
        if cam is not None:
            print("ZED Final count - " + str(frames_recorded))
            cam.disable_recording()
            print("Stopped recording!")
            cam.close()

    def run(self):
        frames_recorded = 0
        while True:
            cam = self.intializeCamera()
            startTime = time.time()
            if cam is not None:
                runtime = sl.RuntimeParameters()
                frames_recorded = 0
                while (time.time()-startTime<self.recording_interval):
                    if self.stopEvent.is_set():
                        self.cleanup(frames_recorded, cam)
                        return
                    if self.pauseEvent.is_set():
                        time.sleep(0.1)
                    else:
                        cam.grab(runtime)
                        image = sl.Mat()
                        cam.retrieve_image(image, sl.VIEW.LEFT)
                        print(image.get_data().shape)
                        frames_recorded += 1
                        # print("Frame count ZED: " + str(frames_recorded), end="\r")
                self.cleanup(frames_recorded, cam)