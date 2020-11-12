import numpy as np
import cv2
import datetime
import signal
import time
import sys
import pyzed.sl as sl
import os
import threading

class ZEDProcess:
    def __init__(self):
        return
    def intializeCamera(self, initParams):
        self.cam = sl.Camera()
        initParams = sl.InitParameters()
        initParams.camera_resolution = sl.RESOLUTION.HD720
        initParams.depth_mode = sl.DEPTH_MODE.PERFORMANCE
        initParams.camera_fps = 15

        status = self.cam.open(initParams)
        if status != sl.ERROR_CODE.SUCCESS:
            print(repr(status))
            self.cam = None

    def startRecording(self):
        if self.recordEvent.is_set() == False:
            self.recordEvent.set()
            self.startTime = datetime.datetime.now()
            self.startUnixTime = time.time()

            startTimeString = self.startTime.strftime("ZED_%Y-%m-%d-%H-%M-%S")
            self.filename = startTimeString+".svo"
            filepath = os.path.join(self.dir, self.filename)
            print("ZED Camera - recording to " + filepath)

            recording_param = sl.RecordingParameters(filepath, sl.SVO_COMPRESSION_MODE.H264)
            self.cam.enable_recording(recording_param)

    def stopRecording(self):
        if self.recordEvent.is_set():
            self.cam.disable_recording()
        self.recordEvent.clear()

    def recordFrame(self):
        if (time.time() - self.startUnixTime > self.recordingInterval):
            self.stopRecording()
            self.startRecording()

    def commandLoop(self):
        while True:
            while not self.commandQueue.empty():
                command = self.commandQueue.get()
                if command == 'REC':
                    self.startRecording()
                elif command == 'STOP':
                    self.stopRecording()
    # FIXME: take ctr properly
    def run(self, initParams, dir, recordingInterval, commandQueue, imageQueue, recordEvent, terminateEvent):
        self.intializeCamera(initParams)
        self.dir = dir
        self.terminateEvent = terminateEvent
        self.recordEvent = recordEvent
        self.recordingInterval = recordingInterval
        self.commandQueue = commandQueue
        self.imageQueue = imageQueue

        if self.cam == None:
            print("ZED Error, terminating process.")
            return
        print("Running ZED Process!")
        threading.Thread(target=self.commandLoop).start()
        sys.stdout.flush()
        while terminateEvent.is_set() == False:
            runtime = sl.RuntimeParameters()
            self.cam.grab(runtime)
            image = sl.Mat()
            self.cam.retrieve_image(image, sl.VIEW.LEFT)

            lastFrame = image.get_data()
            lastFrame = cv2.rotate(lastFrame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            # replace with Q
            imageQueue.put(lastFrame)

            # PAUSE is currently ignored, since disabling cam.grab would disable the stream
            if recordEvent.is_set():
                self.recordFrame()
        if recordEvent.is_set() == True:
            self.cam.disable_recording()
        self.cam.close()