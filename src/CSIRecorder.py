import numpy as np
import cv2
import datetime
import signal
import time
import pickle
import os
import sys

class CSIRecorder:
    def __init__(self, pauseEvent, stopEvent, csiParams = {
        "dir": ".", "streamer": None, "resolution": (640,480), "framerate": 30, "framelock": None
    }, recording_interval = sys.maxsize):
        self.out = None
        self.dir = csiParams['dir']
        self.pauseEvent = pauseEvent
        self.stopEvent = stopEvent
        self.streamer = csiParams['streamer']
        self.framerate = csiParams['framerate']
        self.resolution = csiParams['resolution']
        self.frameLock = csiParams['framelock']
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.recording_interval = recording_interval

    def cleanup(self, frames_recorded, startTimeString, timestamps):
        self.out.release()
        print("CSI Final count - " + str(frames_recorded))
        with open(os.path.join(self.dir, startTimeString+".pkl"), 'wb') as f:
            pickle.dump(timestamps, f)
        print("Stopped recording!")


    def run(self):
        while True:
            now = datetime.datetime.now()
            startTimeString = now.strftime("CSI_%Y-%m-%d-%H-%M-%S")
            filepath = os.path.join(self.dir, startTimeString+".avi")
            print("CSI Camera - recording to " + filepath)
            self.out = cv2.VideoWriter(filepath, self.fourcc, self.framerate, (self.resolution[1], self.resolution[0]))
            frames_recorded = 0
            timestamps = []
            startTime = time.time()
            while (time.time()-startTime<self.recording_interval):
                if self.stopEvent.is_set():
                    self.cleanup(frames_recorded, startTimeString, timestamps)
                    return
                if self.pauseEvent.is_set():
                    time.sleep(0.1)
                else:
                    self.frameLock.acquire()
                    frame = self.streamer.lastFrame
                    timestamp = self.streamer.lastTimestamp
                    self.frameLock.release()
                    freshFrame = True if len(timestamps)==0 or timestamps[-1] < timestamp else False
                    if frame is not None and freshFrame:
                        frames_recorded += 1
                        print("Frame count CSI: " + str(frames_recorded), end="\r")
                        timestamps.append(timestamp)
                        self.out.write(frame)
            self.cleanup(frames_recorded, startTimeString, timestamps)

