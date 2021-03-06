import cv2
import datetime
import os
import pickle
import time
import sys
import cherrypy

class CSIRecorder:
    def __init__(self, dir, recordingResolution, framerate, filenamePrefix, recordingInterval=-1):
        self.RECORDING = False
        self.recordingResolution = recordingResolution
        self.framerate = framerate
        self.dir = dir
        self.filename = ""
        self.out = None
        self.startUnixTime = 0
        self.framesRecorded = 0
        self.filenamePrefix = filenamePrefix
        self.recordingInterval = sys.maxsize if recordingInterval == -1 else recordingInterval

    def startRecording(self):
        if self.RECORDING is False:
            self.framesRecorded = 0
            startTime = datetime.datetime.now()
            self.filename = self.filenamePrefix + "_" + \
                startTime.strftime("%Y-%m-%d-%H-%M-%S")
            self.startUnixTime = time.time()
            cherrypy.log("Recording to - " + self.filename)
            filepath = os.path.join(self.dir, self.filename+".avi")
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.out = cv2.VideoWriter(
                filepath, fourcc, self.framerate, self.recordingResolution)
            self.data = []
            self.RECORDING = True

    def recordData(self, frame, dataItem):
        if frame is None:
            self.stopRecording()
            return
        if (time.time() - self.startUnixTime < self.recordingInterval):
            videoFrame = cv2.resize(
                frame, self.recordingResolution, cv2.INTER_AREA)
            self.out.write(videoFrame)
            self.data.append(dataItem)
            self.framesRecorded += 1
        else:
            self.stopRecording()
            now = datetime.datetime.now()
            self.startRecording()

    def stopRecording(self):
        if self.RECORDING is True:
            self.RECORDING = False
            cherrypy.log("Stopped recording to - " + self.filename)
            filepath = os.path.join(self.dir, self.filename+".pkl")
            t = time.time()-self.startUnixTime
            fps = self.framesRecorded/t
            cherrypy.log("FPS %f Frames %d Time %f" % (fps,self.framesRecorded,t))
            with open(filepath, 'wb') as f:
                pickle.dump(self.data, f)
            # JIALAT!!! out.release() causes crash lah!
            # self.out.release()
