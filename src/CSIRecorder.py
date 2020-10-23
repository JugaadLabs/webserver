import cv2
import datetime
import os
import pickle

class CSIRecorder:
    def __init__(self, dir, recordingResolution, framerate):
        self.RECORDING = False
        self.recordingResolution = recordingResolution
        self.framerate = framerate
        self.dir = dir
        self.filename = ""
        self.out = None

    def startRecording(self, filename):
        if self.RECORDING is False:
            self.filename = filename
            print("Recording to - " + self.filename)
            filepath = os.path.join(self.dir, self.filename+".avi")
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.out = cv2.VideoWriter(
                filepath, fourcc, self.framerate, self.recordingResolution)
            self.data = []
            self.RECORDING = True

    def recordData(self, frame, dataItem):
        videoFrame = cv2.resize(
            frame, self.recordingResolution, cv2.INTER_AREA)
        self.out.write(videoFrame)
        self.data.append(dataItem)

    def stopRecording(self):
        if self.RECORDING is True:
            self.RECORDING = False
            print("Stopped recording to - " + self.filename)
            filepath = os.path.join(self.dir, self.filename+".pkl")
            with open(filepath, 'wb') as f:
                pickle.dump(self.data, f)
            self.out.release()
