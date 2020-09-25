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
from CSIRecorder import CSIRecorder

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
        if process == None:
            print("Process not initialized yet!")
            return
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

    def command_handler(self, device, command):
        if device == 'csi':
            self.camera_handler(self.csiProcess, CSIRecorder, command)
        elif device == 'zed':
            self.camera_handler(self.zedProcess, CSIRecorder, command)
        elif device == 'all':
            self.camera_handler(self.csiProcess, CSIRecorder, command)
            self.camera_handler(self.zedProcess, CSIRecorder, command)
    
    @cherrypy.expose
    def record(self, device=None):
        self.command_handler(device, CameraState.RECORD)
        return "OK"

    @cherrypy.expose
    def pause(self, device=None):
        self.command_handler(device, CameraState.PAUSE)
        return "OK"

    @cherrypy.expose
    def stop(self, device=None):
        self.command_handler(device, CameraState.STOP)
        return "OK"
