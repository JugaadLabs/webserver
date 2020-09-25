import numpy as np
import cv2
import datetime
import multiprocessing
from signal import signal, SIGTERM, SIGALRM, SIGUSR1, SIGUSR2
from CSIRecorder import CSIRecorder
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
    p = CSIRecorder()
    p.start()
    time.sleep(10)
    os.kill(p.pid, SIGUSR1)
    time.sleep(5)
    os.kill(p.pid, SIGUSR1)
    time.sleep(10)
    os.kill(p.pid, SIGUSR2)
    p.join()
    print(p.is_alive())
    # os.kill(p.pid, SIGUSR2)

def main():
    test2()

if __name__=="__main__": 
    main()