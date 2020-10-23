import numpy as np
import cv2
import datetime
import signal
import time
import pickle
import os
import cherrypy

from src.CameraState import CameraState
from src.CSIRecorder import CSIRecorder


class CSIStreamer:
    def __init__(self, frameLock, dir, recordingInterval, device, resolution, recordingResolution, framerate):
        self.device = device
        self.resolution = resolution
        self.cap = None
        self.lastFrame = None
        self.lastTimestamp = time.time()
        self.frameLock = frameLock
        self.recorder = CSIRecorder(dir, recordingResolution, framerate, "CSI", recordingInterval)

    def startRecording(self, startTime):
        self.recorder.startRecording()

    def stopRecording(self):
        self.recorder.stopRecording()

    def isRecording(self):
        return self.recorder.RECORDING

    def run(self):
        print("Starting streaming thread with /dev/video" + str(self.device))
        self.cap = cv2.VideoCapture(self.device)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        while (self.cap.isOpened()):
            state = cherrypy.engine.state
            if state == cherrypy.engine.states.STOPPING or state == cherrypy.engine.states.STOPPED:
                break
            ret, frame = self.cap.read()

            self.frameLock.acquire()
            self.lastFrame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            cherrypy.engine.publish("csiFrame", self.lastFrame)
            self.lastTimestamp = time.time()
            self.frameLock.release()
            if self.recorder.RECORDING == True:
                self.recorder.recordData(self.lastFrame, self.lastTimestamp)
        self.stopRecording()
        print("Disabled streaming thread")
        self.cap.release()
