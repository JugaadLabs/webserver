import numpy as np
import cv2
import datetime
import multiprocessing
from signal import signal, SIGTERM, SIGALRM, SIGUSR1, SIGUSR2
from CSIRecorder import CSIRecorder
# from ZEDRecorder import ZEDRecorder
import time
import os

def test1():
    for i in range(5):
        p = CSIRecorder()
        print(p.is_alive())
        print(p.pid)
        p.start()
        print(p.is_alive())
        print(p.pid)
        time.sleep(5)
        p.terminate()
        p.join()
        print(p.is_alive())
        print(p.pid)

def test2():
    e = multiprocessing.Event()
    e.clear()
    p = CSIRecorder(e)
    p.start()
    time.sleep(10)
    e.set()
    # os.kill(p.pid, SIGUSR1)
    time.sleep(5)
    e.clear()
    # os.kill(p.pid, SIGUSR1)
    time.sleep(10)
    os.kill(p.pid, SIGUSR2)
    p.join()
    print(p.is_alive())
    # os.kill(p.pid, SIGUSR2)

def test3():
    e = multiprocessing.Event()
    p = CSIRecorder(e)
    p.start()
    for i in range(20):
        print(e.is_set())
        time.sleep(0.5)
    # time.sleep(10)

def test4():
    pause = multiprocessing.Event()
    stop = multiprocessing.Event()
    pause.clear()
    stop.clear()
    proc = CSIRecorder(pause, stop, 0, (1344,376))
    proc.start()
    time.sleep(10)
    pause.set()
    time.sleep(5)
    pause.clear()
    time.sleep(10)
    stop.set()
    proc.join()

def test5():
    pause = multiprocessing.Event()
    stop = multiprocessing.Event()
    pause.clear()
    stop.clear()
    proc = ZEDRecorder(pause, stop, None, sl.RESOLUTION.HD720, sl.DEPTH_MODE.PERFORMANCE)
    proc.start()
    time.sleep(10)
    pause.set()
    time.sleep(5)
    pause.clear()
    time.sleep(10)
    stop.set()
    proc.join()

def test6():
    pause = multiprocessing.Event()
    stop = multiprocessing.Event()
    pause.clear()
    stop.clear()
    proc = CSIRecorder(pause, stop, {
        "device": 0, "resolution": (640,480), "framerate": 30, "dir": ""
    })
    proc.start()
    time.sleep(10)
    stop.set()
    proc.join()


def main():
    test6()

if __name__=="__main__": 
    main()