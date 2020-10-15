import numpy as np
import cv2
import datetime
import signal
import time
import sys
import pyzed.sl as sl
import os
from src.CameraState import CameraState

class ZEDStreamer:
    def __init__(self, frameLock, dir, recordingInterval=300, resolution=sl.RESOLUTION.HD720, depth=sl.DEPTH_MODE.PERFORMANCE, framerate=15):
        self.initParams = sl.InitParameters()
        self.initParams.camera_resolution = resolution
        self.initParams.depth_mode = depth
        self.initParams.camera_fps = framerate
        self.lastFrame = None
        self.dir = dir
        self.frameLock = frameLock
        self.currentState = CameraState.STOP
        self.recordingInterval = recordingInterval
        self.cam = self.intializeCamera()

    def intializeCamera(self):
        cam = sl.Camera()
        status = cam.open(self.initParams)
        if status != sl.ERROR_CODE.SUCCESS:
            print(repr(status))
            return None
        else:
            return cam

    def startRecording(self, startTime):
        if self.currentState == CameraState.STOP:
            self.startTime = startTime
            self.startUnixTime = time.time()

            startTimeString = self.startTime.strftime("ZED_%Y-%m-%d-%H-%M-%S")
            filepath = os.path.join(self.dir, startTimeString+".svo")
            print("ZED Camera - recording to " + filepath)

            recording_param = sl.RecordingParameters(filepath, sl.SVO_COMPRESSION_MODE.H264)
            self.cam.enable_recording(recording_param)
        self.currentState = CameraState.RECORD

    def stopRecording(self):
        if self.currentState != CameraState.STOP:
            self.cam.disable_recording()
        self.currentState = CameraState.STOP

    def pauseRecording(self):
        if self.currentState != CameraState.STOP:
            print("ZED Recording paused!")            
            self.currentState = CameraState.PAUSE

    def recordFrame(self):
        if (time.time() - self.startUnixTime > self.recordingInterval):
            self.stopRecording()
            now = datetime.datetime.now()
            self.startRecording(now)

    def run(self):
        while True and self.cam is not None:
            runtime = sl.RuntimeParameters()
            self.cam.grab(runtime)
            image = sl.Mat()
            self.cam.retrieve_image(image, sl.VIEW.LEFT)
            self.lastFrame = image.get_data()
            # PAUSE is currently ignored, since disabling cam.grab would disable the stream
            if self.currentState != CameraState.STOP:
                self.recordFrame()
        if self.currentState != CameraState.STOP:
            self.cam.disable_recording()
        self.cam.close()