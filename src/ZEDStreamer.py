import numpy as np
import cv2
import datetime
import signal
import time
import sys
import pyzed.sl as sl
import os
import cherrypy


class ZEDStreamer:
    def __init__(self, frameLock, dir, recordingInterval, resolution, depth, framerate):
        self.initParams = sl.InitParameters()
        self.initParams.camera_resolution = resolution
        self.initParams.depth_mode = depth
        self.initParams.camera_fps = framerate
        self.lastFrame = None
        self.dir = dir
        self.frameLock = frameLock
        self.RECORDING = False
        self.recordingInterval = recordingInterval
        self.cam = self.intializeCamera()
        self.filename = ""

    def intializeCamera(self):
        cam = sl.Camera()
        status = cam.open(self.initParams)
        if status != sl.ERROR_CODE.SUCCESS:
            print(repr(status))
            return None
        else:
            return cam

    def startRecording(self, startTime):
        if self.RECORDING == False:
            self.startTime = startTime
            self.startUnixTime = time.time()

            startTimeString = self.startTime.strftime("ZED_%Y-%m-%d-%H-%M-%S")
            self.filename = startTimeString+".svo"
            filepath = os.path.join(self.dir, self.filename)
            print("ZED Camera - recording to " + filepath)

            recording_param = sl.RecordingParameters(filepath, sl.SVO_COMPRESSION_MODE.H264)
            self.cam.enable_recording(recording_param)
        self.RECORDING = True

    def isRecording(self):
        return self.RECORDING

    def stopRecording(self):
        if self.RECORDING == True:
            self.cam.disable_recording()
        self.RECORDING = False

    def recordFrame(self):
        if (time.time() - self.startUnixTime > self.recordingInterval):
            self.stopRecording()
            now = datetime.datetime.now()
            self.startRecording(now)

    def run(self):
        if self.cam == None:
            return
        while True:
            runtime = sl.RuntimeParameters()
            self.cam.grab(runtime)
            image = sl.Mat()
            self.cam.retrieve_image(image, sl.VIEW.LEFT)
            self.frameLock.acquire()
            self.lastFrame = image.get_data()
            self.lastFrame = cv2.rotate(self.lastFrame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            cherrypy.engine.publish("zedFrame", self.lastFrame)
            self.frameLock.release()
            # PAUSE is currently ignored, since disabling cam.grab would disable the stream
            if self.RECORDING == True:
                self.recordFrame()
        if self.RECORDING == True:
            self.cam.disable_recording()
        self.cam.close()