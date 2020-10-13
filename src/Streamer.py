import numpy as np
import cv2
import datetime
import signal
import time
import pickle
import os
import cherrypy

class Streamer:
    def __init__(self, frameLock, device=0, resolution= (640,480), framerate= 30):
        self.device = device
        self.framerate = framerate
        self.resolution = resolution
        self.cap = None
        self.lastFrame = None
        self.lastTimestamp = time.time()
        self.frameLock = frameLock

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
        print("Disabled streaming thread")
        self.cap.release()

