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

ZED_ENABLED = True

try:
    import pyzed.sl as sl
except ImportError as e:
    print("pyzed not available! Using V4L2 fallback.")
    ZED_ENABLED = False
else:
    from src.ZEDStreamer import ZEDStreamer

from cherrypy.lib.static import serve_file
from src.templates import Templates
from src.CSIStreamer import CSIStreamer
from src.CameraState import CameraState

class URLHandler(object):
    def __init__(self, recording_dir, csiStreamer, csiFrameLock, zedStreamer, zedFrameLock, csi_device=0, zed_device=1):
        self.recording_dir = os.path.abspath(recording_dir)
        self.calibration_dir = os.path.join(self.recording_dir, "calibration")
        Path(self.calibration_dir).mkdir(parents=True, exist_ok=True)

        self.template = Templates()

        self.csiDevice = csi_device
        self.zedDevice = zed_device

        self.csiStreamer = csiStreamer
        self.csiFrameLock = csiFrameLock

        if ZED_ENABLED:
            self.zedStreamer = zedStreamer
            self.zedFrameLock = zedFrameLock

    def camera_handler(self, streamer, command, t):
        if command == CameraState.RECORD:
            streamer.startRecording(t)
        elif command == CameraState.PAUSE:
            streamer.pauseRecording()
        elif command == CameraState.STOP:
            streamer.stopRecording()

    def getCurrentStatus(self, streamer):
        return streamer.currentState

    def getCurrentStatusText(self, currentStatus):
        if currentStatus == CameraState.RECORD:
            return " is recording."
        elif currentStatus == CameraState.PAUSE:
            return " is paused."
        else:
            return " has stopped recording."

    def command_handler(self, csi, zed, command):
        t = datetime.datetime.now()
        if csi:
            self.camera_handler(self.csiStreamer, command, t)
        if zed and ZED_ENABLED:
            self.camera_handler(self.zedStreamer, command, t)

        csiText = "Mono Camera " + self.getCurrentStatusText(self.getCurrentStatus(self.csiStreamer))
        if ZED_ENABLED:
            zedText = "ZED Depth camera " + self.getCurrentStatusText(self.getCurrentStatus(self.zedStreamer))
        else:
            zedText = "pyzed not detected. ZED camera is disabled."
        return csiText, zedText

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
            frame = self.csiStreamer.lastFrame
            if frame is None:
                continue
            resized = cv2.resize(frame, (int(0.5*frame.shape[1]), int(0.5*frame.shape[0])), cv2.INTER_AREA)
            (flag, encodeImage) = cv2.imencode(".jpg", resized)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +  bytearray(encodeImage) + b'\r\n')
        print("Shutting down!")
        self.command_handler(True, True, CameraState.STOP)

    @cherrypy.expose
    def zedStream(self):
        cherrypy.response.headers['Content-Type'] = "multipart/x-mixed-replace; boundary=zedframe"
        if ZED_ENABLED:
            return self.getZedFrame()
        return
    zedStream._cp_config = {'response.stream': True}

    def getZedFrame(self):
        while True:
            state = cherrypy.engine.state
            if state == cherrypy.engine.states.STOPPING or state == cherrypy.engine.states.STOPPED:
                break
            frame = self.zedStreamer.lastFrame
            if frame is None:
                continue
            resized = cv2.resize(frame, (int(0.5*frame.shape[0]), int(0.5*frame.shape[1])), cv2.INTER_AREA)
            (flag, encodeImage) = cv2.imencode(".jpg", resized)
            if flag:
                yield(b'--zedframe\r\n' b'Content-Type: image/jpeg\r\n\r\n' +  bytearray(encodeImage) + b'\r\n')
        print("Shutting down ZED!")

    @cherrypy.expose
    def download(self, filepath):
        return serve_file(filepath, "application/x-download", "attachment")

    @cherrypy.expose
    def ls(self, dir=None):
        if dir is None:
            dir = self.recording_dir
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
        csi = True if csi=='true' else False
        zed = True if zed=='true' else False
        csiText, zedText = self.command_handler(csi, zed, action)
        cherrypy.response.headers['Content-Type'] = 'text/markdown'
        return simplejson.dumps(dict(csi=csiText, zed=zedText))

    @cherrypy.expose
    def record(self, csi, zed):
        return self.executeAction(csi, zed, CameraState.RECORD)

    @cherrypy.expose
    def pause(self, csi='False', zed='False'):
        return self.executeAction(csi, zed, CameraState.PAUSE)

    @cherrypy.expose
    def stop(self, csi='False', zed='False'):
        return self.executeAction(csi, zed, CameraState.STOP)

    @cherrypy.expose
    def data(self):
        return self.template.data(ZED_ENABLED)

    @cherrypy.expose
    def captureImage(self):
        self.csiFrameLock.acquire()
        frame = cv2.cvtColor(self.csiStreamer.lastFrame, cv2.COLOR_BGR2RGB)
        self.csiFrameLock.release()
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