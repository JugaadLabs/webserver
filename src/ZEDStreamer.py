import numpy as np
import cv2
import datetime
import signal
import time
import sys
import pyzed.sl as sl
import os
import cherrypy
import multiprocessing

from src.ZEDProcess import ZEDProcess


class ZEDStreamer:
    def __init__(self, frameLock, dir, recordingInterval, resolution, depth, framerate):
        initParams = sl.InitParameters()
        initParams.camera_resolution = resolution
        initParams.depth_mode = depth
        initParams.camera_fps = framerate
        self.filename = ""
        self.lastFrame = None
        multiprocessing.set_start_method('spawn')

        self.recordEvent = multiprocessing.Event()
        self.terminateEvent = multiprocessing.Event()
        self.recordEvent.clear()
        self.terminateEvent.clear()
        self.commandQueue = multiprocessing.Queue()
        self.imageQueue = multiprocessing.Queue()
        zedProcessObject = ZEDProcess()
        multiprocessing.Process(target=zedProcessObject.run, args=(
            None, dir, recordingInterval, self.commandQueue, self.imageQueue, self.recordEvent, self.terminateEvent,)).start()

    def startRecording(self, startTime):
        self.commandQueue.put('REC')
        self.startTime = startTime
        self.startUnixTime = time.time()

        startTimeString = self.startTime.strftime("ZED_%Y-%m-%d-%H-%M-%S")
        self.filename = startTimeString+".svo"

    def isRecording(self):
        return self.recordEvent.is_set()

    def stopRecording(self):
        self.commandQueue.put('STOP')

    def run(self):
        while True:
            while not self.imageQueue.empty():
                self.lastFrame = self.imageQueue.get()
                cherrypy.engine.publish("zedFrame", self.lastFrame)