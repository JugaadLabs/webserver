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
from ZEDRecorder import ZEDRecorder
import threading
import enum
from templates import Templates

class CameraState(enum.Enum):
    RECORD = 1
    PAUSE = 2
    STOP = 3

class URLHandler(object):
    def __init__(self, config):
        self.config = config
        self.csiThread = None
        self.zedThread = None

        self.csiPause = threading.Event()
        self.csiStop = threading.Event()
        self.zedPause = threading.Event()
        self.zedStop = threading.Event()

        self.csiPause.clear()
        self.csiStop.set()
        self.zedPause.clear()
        self.zedStop.set()

        stateVars = {}
        stateVars['zedstop'] = self.zedStop
        stateVars['zedpaused'] = self.zedPause
        stateVars['csistop'] = self.csiStop
        stateVars['csipaused'] = self.csiPause
        self.template = Templates(stateVars)

    def camera_handler(self, cameraThread, cameraClass, pauseEvent, stopEvent, command):
        if cameraThread == None and command != CameraState.RECORD:
            print("Process not initialized yet!")
        else:
            if command == CameraState.RECORD:
                if cameraThread is not None and cameraThread.is_alive():
                    print("Camera already active!")
                    if pauseEvent.is_set():
                        print("Resuming recording...")
                        pauseEvent.clear()
                else:
                    stopEvent.clear()
                    pauseEvent.clear()
                    cc = cameraClass(pauseEvent, stopEvent)
                    cameraThread = threading.Thread(None, cc.run)
                    cameraThread.start()
            elif command == CameraState.PAUSE:
                if cameraThread is not None and cameraThread.is_alive():
                    pauseEvent.set()
                else:
                    print("Camera not started")
            elif command == CameraState.STOP:
                if cameraThread is not None and cameraThread.is_alive():
                    stopEvent.set()
                else:
                    print("Camera not yet started")
        return cameraThread, pauseEvent, stopEvent

    def command_handler(self, device, command):
        if device == 'csi':
            self.csiThread, self.csiPause, self.csiStop = self.camera_handler(self.csiThread, \
            CSIRecorder, self.csiPause, self.csiStop, command)
        elif device == 'zed':
            self.zedThread, self.zedPause, self.zedStop = self.camera_handler(self.zedThread, \
            ZEDRecorder, self.zedPause, self.zedStop, command)
        elif device == 'all':
            self.csiThread, self.csiPause, self.csiStop = self.camera_handler(self.csiThread, \
            CSIRecorder, self.csiPause, self.csiStop, command)
            self.zedThread, self.zedPause, self.zedStop = self.camera_handler(self.zedThread, \
            ZEDRecorder, self.zedPause, self.zedStop, command)

    @cherrypy.expose
    def record(self, device=None):
        self.command_handler(device, CameraState.RECORD)
        return self.template.index()

    @cherrypy.expose
    def pause(self, device=None):
        self.command_handler(device, CameraState.PAUSE)
        return self.template.index()

    @cherrypy.expose
    def stop(self, device=None):
        self.command_handler(device, CameraState.STOP)
        return self.template.index()

    @cherrypy.expose
    def index(self):
        return self.template.index()