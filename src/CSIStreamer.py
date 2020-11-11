import numpy as np
import cv2
import datetime
import signal
import time
import pickle
import os
import cherrypy
import threading

from src.CameraState import CameraState
from src.CSIRecorder import CSIRecorder


class CSIStreamer:
    def __init__(self, frameLock, dir, recordingInterval, device, stdResolution, hdResolution, recordingResolution, framerate):
        self.device = device
        self.stdResolution = stdResolution
        self.hdResolution = hdResolution
        self.cap = None
        self.lastFrame = None
        self.lastTimestamp = time.time()
        self.frameLock = frameLock
        self.recorder = CSIRecorder(dir, recordingResolution, framerate, "CSI", recordingInterval)
        # self.cap = cv2.VideoCapture(self.device)
        self.setResolution(False)
        cherrypy.engine.subscribe("hdResolution", self.setResolution)

    def startRecording(self, startTime):
        self.setResolution(False)
        self.recorder.startRecording()

    def stopRecording(self):
        self.recorder.stopRecording()

    def isRecording(self):
        return self.recorder.RECORDING

    def setResolution(self, HDResolution):
        if self.cap is not None:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.device)
        if HDResolution:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.hdResolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.hdResolution[1])
        else:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.stdResolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.stdResolution[1])
        threading.Thread(None, self.run).start()

    def run(self):
        print("Starting streaming thread with /dev/video" + str(self.device))
        while (self.cap.isOpened()):
            state = cherrypy.engine.state
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
