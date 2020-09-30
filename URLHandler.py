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
import enum
import multiprocessing
from templates import Templates

class CameraState(enum.Enum):
    RECORD = 1
    PAUSE = 2
    STOP = 3

class URLHandler(object):
    def __init__(self, config):
        self.config = config
        self.csiProcess = None
        self.zedProcess = None

        self.csiPause = multiprocessing.Event()
        self.csiStop = multiprocessing.Event()
        self.zedPause = multiprocessing.Event()
        self.zedStop = multiprocessing.Event()

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

    def camera_handler(self, process, cameraClass, pauseEvent, stopEvent, command):
        if process == None and command != CameraState.RECORD:
            print("Process not initialized yet!")
        else:
            if command == CameraState.RECORD:
                if process is not None and process.is_alive():
                    print("Camera already active!")
                    if pauseEvent.is_set():
                        print("Resuming recording...")
                        pauseEvent.clear()
                else:
                    stopEvent.clear()
                    pauseEvent.clear()
                    process = cameraClass(pauseEvent, stopEvent)
                    process.start()
            elif command == CameraState.PAUSE:
                if process is not None and process.is_alive():
                    pauseEvent.set()
                else:
                    print("Camera not started")
            elif command == CameraState.STOP:
                if process is not None and process.is_alive():
                    stopEvent.set()
                else:
                    print("Camera not yet started")
        return process, pauseEvent, stopEvent

    def command_handler(self, device, command):
        if device == 'csi':
            self.csiProcess, self.csiPause, self.csiStop = self.camera_handler(self.csiProcess, \
            CSIRecorder, self.csiPause, self.csiStop, command)
        elif device == 'zed':
            self.zedProcess, self.zedPause, self.zedStop = self.camera_handler(self.zedProcess, \
            ZEDRecorder, self.zedPause, self.zedStop, command)
        elif device == 'all':
            self.csiProcess, self.csiPause, self.csiStop = self.camera_handler(self.csiProcess, \
            CSIRecorder, self.csiPause, self.csiStop, command)
            self.zedProcess, self.zedPause, self.zedStop = self.camera_handler(self.zedProcess, \
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