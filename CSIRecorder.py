import numpy as np
import cv2
import datetime
import multiprocessing
from signal import signal, SIGTERM

class CSIRecorder(multiprocessing.Process):
    def __init__(self, device=0, resolution=(640,480), framerate=30):
        super(CSIRecorder, self).__init__()
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.device = device
        self.resolution = resolution
        self.framerate = framerate
        self.cap = None
        self.out = None

    def run(self):
        self.cap = cv2.VideoCapture(self.device)
        self.out = cv2.VideoWriter('output.avi', self.fourcc, self.framerate, self.resolution)
        while(self.cap.isOpened()):
            ret, frame = self.cap.read()
            if ret==True:
                frame = cv2.flip(frame,0)
                self.out.write(frame)
            else:
                break

    def handler(self, signal_received, frame):
        self.cap.release()
        self.out.release()
        print("Quitting execution")
