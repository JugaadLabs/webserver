import numpy as np
import cv2
import datetime
import multiprocessing
import signal
import time
import pickle
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
        self.dir = dir
        self.pauseEvent = pauseEvent
        self.stopEvent = stopEvent

    def run(self):
        self.cap = cv2.VideoCapture(self.device)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        now = datetime.datetime.now()
        startTimeString = now.strftime("CSI_%Y-%m-%d-%H-%M-%S")
        filename = startTimeString+".avi"
        print("CSI Camera - recording to " + filename)
        self.out = cv2.VideoWriter(filename, self.fourcc, self.framerate, self.resolution)
        frames_recorded = 0
        timestamps = []
        while(self.cap.isOpened() and not self.stopEvent.is_set()):
            if not self.pauseEvent.is_set():
                ret, frame = self.cap.read()
                if ret==True:
                    frames_recorded += 1
                    print("Frame count: " + str(frames_recorded), end="\r")
                    timestamps.append(time.time())
                    self.out.write(frame)
                else:
                    break
            else:
                time.sleep(0.1)
        self.cap.release()
        self.out.release()
        timestamp_pkl = open(startTimeString+".pkl", 'rb')
        pickle.dump(timestamps, timestamps)
        timestamp_pkl.close()
        print("Stopped recording!")