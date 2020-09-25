import os
import sys
import string
import subprocess
import time
import traceback
import threading
import cherrypy
import jinja2
import signal

class CameraState(Enum):
    RECORD = 1
    PAUSE = 2
    STOP = 3

class URLHandler(object):
    def __init__(self, config):
        self.config = config
        self.csiProcess = None
        self.zedProcess = None

    def camera_handler(self, process, cameraClass, command):
        if command == CameraState.RECORD:
            if process.is_alive():
                print("Camera already active!")
            else:
                process = cameraClass()
                process.start()
        elif command == CameraState.PAUSE:
            if process.is_alive():
                os.kill(process.pid, signal.SIGUSR1)
            else:
                print("Camera not started")
        elif command == CameraState.STOP:
            if process.is_alive():
                os.kill(process.pid, signal.SIGUSR2)
                process.join()
            else:
                print("Camera not started")

    @cherrypy.expose
    def record(self, device=None):
        if device == 'csi':
            print(device)
        elif device == 'zed':
            print(device)
        elif device == 'all':
            print(device)
        return "OK"

    @cherrypy.expose
    def pause(self, device=None):
        if device == 'csi':
            print(device)
        elif device == 'zed':
            print(device)
        elif device == 'all':
            print(device)
        return "OK"

    @cherrypy.expose
    def stop(self, device=None):
        if device == 'csi':
            print(device)
        elif device == 'zed':
            print(device)
        elif device == 'all':
            print(device)
        return "OK"
