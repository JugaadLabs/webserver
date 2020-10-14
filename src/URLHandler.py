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
import datetime
from PIL import Image
import simplejson
from pathlib import Path
from src.calibration.calibrate import *

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
    def __init__(self, config, recording_dir, csi_device=0, zed_device=1, recording_interval=0):
        self.config = config
        self.recording_dir = os.path.abspath(recording_dir)
        self.calibration_dir = os.path.join(self.recording_dir, "calibration")
        Path(self.calibration_dir).mkdir(parents=True, exist_ok=True)

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

        self.csiDevice = csi_device
        self.zedDevice = zed_device

        self.streamer = Streamer(self.frameLock, self.csiDevice)
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

    def command_handler(self, csi, zed, command):
        if csi:
            self.csiThread, self.csiPause, self.csiStop = self.camera_handler(self.csiThread, \
            CSIRecorder, self.csiParams, self.csiPause, self.csiStop, command)
        if zed and ZED_ENABLED:
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
            resized = cv2.resize(frame, (int(0.5*frame.shape[1]), int(0.5*frame.shape[0])), cv2.INTER_AREA)
            (flag, encodeImage) = cv2.imencode(".jpg", resized)
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

    def executeAction(self, csi, zed, action):
        csi = True if csi=='True' else False
        zed = True if zed=='True' else False
        self.command_handler(csi, zed, action)
        return self.template.data()

    @cherrypy.expose
    def record(self, csi='False', zed='False'):
        return self.executeAction(csi, zed, CameraState.RECORD)

    @cherrypy.expose
    def pause(self, csi='False', zed='False'):
        return self.executeAction(csi, zed, CameraState.PAUSE)

    @cherrypy.expose
    def stop(self, csi='False', zed='False'):
        return self.executeAction(csi, zed, CameraState.STOP)

    @cherrypy.expose
    def data(self):
        return self.template.data()

    @cherrypy.expose
    def captureImage(self):
        self.frameLock.acquire()
        frame = cv2.cvtColor(self.streamer.lastFrame, cv2.COLOR_BGR2RGB)
        self.frameLock.release()
        im = Image.fromarray(frame)
        now = datetime.datetime.now()
        filename = now.strftime("IMG_%Y-%m-%d-%H-%M-%S")+".jpeg"
        im.save(os.path.join(self.calibration_dir, filename))

        cherrypy.response.headers['Content-Type'] = 'text/markdown'
        return simplejson.dumps(dict(filename=filename))

    @cherrypy.expose
    def intrinsics(self, command=""):
        return self.template.intrinsics()

    @cherrypy.expose
    def intrinsicCalibration(self):
        calibrationThread = threading.Thread(None, intrinsicCalibration,args=(self.calibration_dir,))
        calibrationThread.start()
        cherrypy.response.headers['Content-Type'] = 'text/markdown'
        return "Calibrating. Check the calibration directory for results."

    @cherrypy.expose
    def index(self):
        if self.csiDevice != -1 and self.zedDevice != -1:
            raise cherrypy.HTTPRedirect("/data")
        msg = "<h1>Error</h1>"
        if self.zedDevice == -1:
            msg += "ZED2 not detected.<br>"
        if self.csiDevice == -1:
            msg += "Monocam not detected.<br>"
        msg += "Please connect the missing camera(s) and restart the Jetson." \
        " You can still choose to record data from the available cameras, view recordings, or read the documentation."
        return self.template.index(msg)
