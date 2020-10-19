import numpy as np
import cv2
import datetime
import signal
import time
import pickle
import os
import cherrypy
from src.CameraState import CameraState

class CSIStreamer:
    def __init__(self, frameLock, dir, recordingInterval=300, device=0, resolution= (640,480), framerate= 30):
        self.device = device
        self.framerate = framerate
        self.resolution = resolution
        self.cap = None
        self.lastFrame = None
        self.lastTimestamp = time.time()
        self.dir = dir
        self.frameLock = frameLock
        self.currentState = CameraState.STOP
        self.recordingInterval = recordingInterval
        self.filename = ""

    def startRecording(self, startTime):
        if self.currentState == CameraState.STOP:
            self.startTime = startTime
            self.startUnixTime = time.time()

            startTimeString = self.startTime.strftime("CSI_%Y-%m-%d-%H-%M-%S")
            self.filename = startTimeString+".avi"
            filepath = os.path.join(self.dir, self.filename)
            print("CSI Camera - recording to " + filepath)

            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.out = cv2.VideoWriter(filepath, fourcc, self.framerate, (self.resolution[1], self.resolution[0]))
            self.timestamps = []
        self.currentState = CameraState.RECORD

    def stopRecording(self):
        if self.currentState != CameraState.STOP:
            startTimeString = self.startTime.strftime("CSI_%Y-%m-%d-%H-%M-%S")
            filepath = os.path.join(self.dir, startTimeString+".pkl")
            with open(filepath, 'wb') as f:
                pickle.dump(self.timestamps, f)
            print("Stopped recording!")
            self.out.release()
        self.currentState = CameraState.STOP

    def recordFrame(self):
        if (time.time() - self.startUnixTime < self.recordingInterval):
            self.timestamps.append(self.lastTimestamp)
            self.out.write(self.lastFrame)
        else:
            self.stopRecording()
            now = datetime.datetime.now()
            self.startRecording(now)

    def getCurrentFrame(self):
        self.frameLock.acquire()
        frame = self.lastFrame
        self.frameLock.release()
        return frame

    def run(self):
        print("Starting streaming thread with /dev/video"+ str(self.device))
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
            self.lastTimestamp = time.time()
            self.frameLock.release()
            if self.currentState == CameraState.RECORD:
                self.recordFrame()
        if self.currentState != CameraState.STOP:
            self.stopRecording()
        print("Disabled streaming thread")
        self.cap.release()

