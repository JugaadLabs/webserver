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
import threading
import enum
import glob
import cv2

ZED_ENABLED = True

try:
    import pyzed.sl as sl
except ImportError as e:
    print("pyzed not available! Using V4L2 fallback.")
    ZED_ENABLED = False
else:
    from src.ZEDRecorder import ZEDRecorder

from cherrypy.lib.static import serve_file
from src.CSIRecorder import CSIRecorder
from src.templates import Templates
from src.Streamer import Streamer

class CameraState(enum.Enum):
    RECORD = 1
    PAUSE = 2
    STOP = 3

class URLHandler(object):
    def __init__(self, config, recording_dir, csi_device=0, recording_interval=0):
        self.config = config
        self.recording_dir = recording_dir

        self.streamThread = None
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

        self.frameLock = threading.Lock()

        self.streamer = Streamer(self.frameLock, csi_device)
        self.streamThread = threading.Thread(None, self.streamer.run, daemon=True)
        self.streamThread.start()

        self.csiParams = {
            "streamer": self.streamer, "resolution": (640,480), 
            "framerate": 30, "dir": recording_dir, "framelock": self.frameLock
        }
        if ZED_ENABLED:
            self.zedParams = {
                "resolution": sl.RESOLUTION.HD720, "depth": sl.DEPTH_MODE.PERFORMANCE, 
                "framerate": 30, "dir": recording_dir
            }

        self.recording_interval = sys.maxsize if recording_interval == 0 else recording_interval

    def camera_handler(self, cameraThread, cameraClass, cameraParams, pauseEvent, stopEvent, command):
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
                    cc = cameraClass(pauseEvent, stopEvent, cameraParams, self.recording_interval)
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
                    cameraThread.join()
                else:
                    print("Camera not yet started")
        return cameraThread, pauseEvent, stopEvent

    def command_handler(self, device, command):
        if device == 'csi':
            self.csiThread, self.csiPause, self.csiStop = self.camera_handler(self.csiThread, \
            CSIRecorder, self.csiParams, self.csiPause, self.csiStop, command)
        elif device == 'zed' and ZED_ENABLED:
            self.zedThread, self.zedPause, self.zedStop = self.camera_handler(self.zedThread, \
            ZEDRecorder, self.zedParams, self.zedPause, self.zedStop, command)
        elif device == 'all' and ZED_ENABLED:
            self.csiThread, self.csiPause, self.csiStop = self.camera_handler(self.csiThread, \
            CSIRecorder, self.csiParams, self.csiPause, self.csiStop, command)
            self.zedThread, self.zedPause, self.zedStop = self.camera_handler(self.zedThread, \
            ZEDRecorder, self.zedParams, self.zedPause, self.zedStop, command)

    @cherrypy.expose
    def stream(self):
        cherrypy.response.headers['Content-Type'] = "multipart/x-mixed-replace; boundary=frame"
        return self.getFrame()
    stream._cp_config = {'response.stream': True}

    def getFrame(self):
        while True:
            state = cherrypy.engine.state
            if state == cherrypy.engine.states.STOPPING or state == cherrypy.engine.states.STOPPED:
                break
            frame = self.streamer.lastFrame
            if frame is None:
                continue
            (flag, encodeImage) = cv2.imencode(".jpg", frame)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +  bytearray(encodeImage) + b'\r\n')
        self.streamThread.join()

    @cherrypy.expose
    def download(self, filepath):
        return serve_file(filepath, "application/x-download", "attachment")

    @cherrypy.expose
    def ls(self, dir=None):
        if dir is None:
            dir = self.recording_dir
        html = """<html><body><h1>Recordings</h1>
        <a href="ls?dir=%s">Up</a><br />
        """ % os.path.dirname(os.path.abspath(dir))
        dirs = []
        files = []
        for filename in glob.glob(dir + '/*'):
            absPath = os.path.abspath(filename)
            item = {}
            item['filename'] = os.path.basename(filename)
            item['path'] = absPath
            if os.path.isdir(absPath):
                dirs.append(item)
            else:
                files.append(item)
        return self.template.ls(files, dirs)

    @cherrypy.expose
    def documentation(self):
        return self.template.documentation()

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