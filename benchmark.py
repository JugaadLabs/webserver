import numpy as np
import cv2
import datetime
import multiprocessing
from signal import signal, SIGTERM, SIGALRM, SIGUSR1, SIGUSR2
from CSIRecorder import CSIRecorder
from ZEDRecorder import ZEDRecorder
import time
import os
import pyzed.sl as sl

def benchmark(res, depth, framerate, time=20):
    pause = multiprocessing.Event()
    stop = multiprocessing.Event()
    pause.clear()
    stop.clear()
    proc = ZEDRecorder(pause, stop, None, res, depth)
    proc.start()
    time.sleep(time)
    stop.set()
    proc.join()

def main():
    benchmark(sl.RESOLUTION.HD720, sl.DEPTH_MODE.PERFORMANCE, 30)
    benchmark(sl.RESOLUTION.HD720, sl.DEPTH_MODE.QUALITY, 30)
    benchmark(sl.RESOLUTION.HD720, sl.DEPTH_MODE.ULTRA, 30)

    benchmark(sl.RESOLUTION.HD720, sl.DEPTH_MODE.PERFORMANCE, 60)
    benchmark(sl.RESOLUTION.HD720, sl.DEPTH_MODE.QUALITY, 60)
    benchmark(sl.RESOLUTION.HD720, sl.DEPTH_MODE.ULTRA, 60)

if __name__=="__main__": 
    main()