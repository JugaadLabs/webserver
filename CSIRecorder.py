import numpy as np
import cv2
import datetime
import multiprocessing
import signal
import time

class CSIRecorder(multiprocessing.Process):
    def __init__(self, device=0, resolution=(640,480), framerate=30, dir=""):
        super(CSIRecorder, self).__init__()
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.device = device
        self.resolution = resolution
        self.framerate = framerate
        self.cap = None
        self.out = None
        self.dir = dir
        self.paused = False
        signal.signal(signal.SIGUSR1, self.handler)
        signal.signal(signal.SIGUSR2, self.handler)

    def run(self):
        self.cap = cv2.VideoCapture(self.device)
        now = datetime.datetime.now()
        filename = now.strftime("%Y-%m-%d-%H-%M-%S")+".avi"
        self.out = cv2.VideoWriter(filename, self.fourcc, self.framerate, self.resolution)
        while(self.cap.isOpened()):
            if self.paused == False:
                ret, frame = self.cap.read()
                if ret==True:
                    self.out.write(frame)
                else:
                    break
            else:
                time.sleep(0.5)

    def handler(self, signal_received, frame):
        # sigusr1 - toggle pause
        # sigusr2 - stop
        if signal_received == signal.SIGUSR1:
            self.paused = not self.paused
            print("Toggling Recording!")
        elif signal_received == signal.SIGUSR2:
            self.cap.release()
            self.out.release()
            print("Stopped recording!")
