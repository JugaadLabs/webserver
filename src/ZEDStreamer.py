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
        self.filename = ""
        self.lastFrame = None
        multiprocessing.set_start_method('spawn')

        self.recordEvent = multiprocessing.Event()
        self.terminateEvent = multiprocessing.Event()
        self.recordEvent.clear()
        self.terminateEvent.clear()
        self.commandQueue = multiprocessing.Queue(maxsize=1)
        self.imageQueue = multiprocessing.Queue(maxsize=5)
        zedProcessObject = ZEDProcess()
        proc = multiprocessing.Process(target=zedProcessObject.run, args=(
            resolution, depth, framerate, dir, recordingInterval, self.commandQueue, self.imageQueue, self.recordEvent, self.terminateEvent,))
        proc.daemon = True
        proc.start()

    def startRecording(self, startTime):
        self.commandQueue.put('REC')
        self.startTime = startTime
        self.startUnixTime = time.time()

        startTimeString = self.startTime.strftime("ZED_%Y-%m-%d-%H-%M-%S")
        self.filename = startTimeString+".svo"

    def isRecording(self):
        time.sleep(0.15)
        return self.recordEvent.is_set()

    def stopRecording(self):
        self.commandQueue.put('STOP')

    def run(self):
        while True:
            while not self.imageQueue.empty():
                self.lastFrame = self.imageQueue.get()
                cherrypy.engine.publish("zedFrame", self.lastFrame)
