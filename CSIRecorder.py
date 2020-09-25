import numpy as np
import cv2
import datetime
import multiprocessing
import signal
import time

class CSIRecorder(multiprocessing.Process):
    def __init__(self, pauseEvent, stopEvent, device=0, resolution=(640,480), framerate=30, dir=""):
        super(CSIRecorder, self).__init__()
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.device = device
        self.resolution = resolution
        self.framerate = framerate
        self.cap = None
        self.out = None
        self.dir = dir
        self.pauseEvent = pauseEvent
        self.stopEvent = stopEvent

    def run(self):
        self.cap = cv2.VideoCapture(self.device)
        now = datetime.datetime.now()
        filename = now.strftime("CSI_%Y-%m-%d-%H-%M-%S")+".avi"
        print("CSI Camera - recording to " + filename)
        self.out = cv2.VideoWriter(filename, self.fourcc, self.framerate, self.resolution)
        while(self.cap.isOpened() and not self.stopEvent.is_set()):
            if not self.pauseEvent.is_set():
                ret, frame = self.cap.read()
                if ret==True:
                    self.out.write(frame)
                else:
                    break
            else:
                time.sleep(0.5)
                print("paused")
        self.cap.release()
        self.out.release()
        print("Stopped recording!")