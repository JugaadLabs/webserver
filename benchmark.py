import numpy as np
import cv2
import datetime
import multiprocessing
from signal import signal, SIGTERM, SIGALRM, SIGUSR1, SIGUSR2
from src.CSIRecorder import CSIRecorder
from src.ZEDRecorder import ZEDRecorder
import time
import os
import pyzed.sl as sl

def benchmark(res, depth, framerate, t=20):
    pause = multiprocessing.Event()
    stop = multiprocessing.Event()
    pause.clear()
    stop.clear()
    params = {"resolution": res, "depth": depth, "framerate": framerate, "dir": ""}
    proc = ZEDRecorder(pause, stop, params)
    proc.start()
    time.sleep(t)
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