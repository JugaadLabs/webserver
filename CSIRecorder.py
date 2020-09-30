import numpy as np
import cv2
import datetime
import multiprocessing
import signal
import time
import pickle
import os

class CSIRecorder(multiprocessing.Process):
    def __init__(self, pauseEvent, stopEvent, csiParams = {
        "device": 0, "resolution": (640,480), "framerate": 30, "dir": ""
    }):
        super(CSIRecorder, self).__init__()
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.device = csiParams['device']
        self.resolution = csiParams['resolution']
        self.framerate = csiParams['framerate']
        self.cap = None
        self.out = None
        self.dir = csiParams['dir']
        self.pauseEvent = pauseEvent
        self.stopEvent = stopEvent

    def run(self):
        self.cap = cv2.VideoCapture(self.device)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        now = datetime.datetime.now()
        startTimeString = now.strftime("CSI_%Y-%m-%d-%H-%M-%S")
        filepath = os.path.join(self.dir, startTimeString+".avi")
        print("CSI Camera - recording to " + filepath)
        self.out = cv2.VideoWriter(filepath, self.fourcc, self.framerate, self.resolution)
        frames_recorded = 0
        timestamps = []
        while(self.cap.isOpened() and not self.stopEvent.is_set()):
            if not self.pauseEvent.is_set():
                ret, frame = self.cap.read()
                if ret==True:
                    frames_recorded += 1
                    # print("Frame count CSI: " + str(frames_recorded), end="\r")
                    timestamps.append(time.time())
                    self.out.write(frame)
                else:
                    break
            else:
                time.sleep(0.1)
        self.cap.release()
        self.out.release()
        print("CSI Final count - " + str(frames_recorded))
        with open(os.path.join(self.dir, startTimeString+".pkl"), 'wb') as f:
            pickle.dump(timestamps, f)
        print("Stopped recording!")