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
import enum
import glob
import cv2
import datetime
from PIL import Image
import simplejson
from pathlib import Path
from operator import itemgetter
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
    def __init__(self, recording_dir, csiStreamer, csiFrameLock, zedStreamer, zedFrameLock, csiStatus=False, zedStatus=False):
        self.recording_dir = os.path.abspath(recording_dir)
        self.calibration_dir = os.path.join(self.recording_dir, "calibration")
        Path(self.calibration_dir).mkdir(parents=True, exist_ok=True)

        self.template = Templates()

        self.csiStatus = csiStatus
        self.zedStatus = zedStatus
        global ZED_ENABLED
        if zedStatus == False:
            ZED_ENABLED = False

        self.csiStreamer = csiStreamer
        self.csiFrameLock = csiFrameLock

        if ZED_ENABLED:
            self.zedStreamer = zedStreamer
            self.zedFrameLock = zedFrameLock

    def camera_handler(self, streamer, command, t):
        if command == CameraState.RECORD:
            streamer.startRecording(t)
        elif command == CameraState.STOP:
            streamer.stopRecording()

    def getCurrentStatus(self, streamer):
        return streamer.currentState

    def getCurrentStatusText(self, currentStatus, filename):
        if currentStatus == CameraState.RECORD:
            return " is recording to " + filename + "."
        elif currentStatus == CameraState.STOP:
            return " file saved to " + filename + "."

    def commandHandler(self, csi, zed, command):
        t = datetime.datetime.now()
        if csi:
            self.camera_handler(self.csiStreamer, command, t)
        if zed and ZED_ENABLED:
            self.camera_handler(self.zedStreamer, command, t)

    def getCameraStatus(self):
        csiFilename = self.csiStreamer.filename
        if csiFilename == "":
            csiText = "Mono Camera is streaming."
        else:
            csiText = "Mono Camera " + self.getCurrentStatusText(self.getCurrentStatus(self.csiStreamer), csiFilename)
        if ZED_ENABLED:
            zedFilename = self.zedStreamer.filename
            if zedFilename == "":
                zedText = "ZED Depth Camera is streaming."
            else:
                zedText = "ZED Depth Camera " + self.getCurrentStatusText(self.getCurrentStatus(self.zedStreamer), zedFilename)
        else:
            zedText = "pyzed not installed or ZED Depth Camera not connected. ZED Recording disabled."
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
        self.commandHandler(True, True, CameraState.STOP)
        # FIXME: not a very good shutdown approach
        sys.exit(0)

    @cherrypy.expose
    def zedStream(self):
        cherrypy.response.headers['Content-Type'] = "multipart/x-mixed-replace; boundary=zedframe"
        if ZED_ENABLED:
            return self.getZedFrame()
        # TODO: needs to be a yield with header
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
            resized = cv2.resize(frame, (int(0.5*frame.shape[1]), int(0.5*frame.shape[0])), cv2.INTER_AREA)
            (flag, encodeImage) = cv2.imencode(".jpg", resized)
            if flag:
                yield(b'--zedframe\r\n' b'Content-Type: image/jpeg\r\n\r\n' +  bytearray(encodeImage) + b'\r\n')
        print("Shutting down ZED!")

    @cherrypy.expose
    def camerastatus(self):
        csiText, zedText = self.getCameraStatus()
        cherrypy.response.headers['Content-Type'] = 'text/markdown'
        return simplejson.dumps(dict(csi=csiText, zed=zedText))

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
        dirs = sorted(dirs, key=itemgetter('filename'))
        files = sorted(files, key=itemgetter('filename'))
        return self.template.ls(files, dirs)

    @cherrypy.expose
    def documentation(self):
        return self.template.documentation()

    def executeAction(self, csi, zed, action):
        csi = True if csi=='true' else False
        zed = True if zed=='true' else False
        self.commandHandler(csi, zed, action)
        return self.camerastatus()

    @cherrypy.expose
    def record(self, csi, zed):
        return self.executeAction(csi, zed, CameraState.RECORD)

    @cherrypy.expose
    def stop(self, csi='False', zed='False'):
        return self.executeAction(csi, zed, CameraState.STOP)

    @cherrypy.expose
    def data(self):
        return self.template.data(ZED_ENABLED)

    @cherrypy.expose
    def captureImage(self):
        now = datetime.datetime.now()
        fileTime = now.strftime("IMG_%Y-%m-%d-%H-%M-%S")+".jpeg"

        self.csiFrameLock.acquire()
        csiFrame = cv2.cvtColor(self.csiStreamer.lastFrame, cv2.COLOR_BGR2RGB)
        self.csiFrameLock.release()
        csiImage = Image.fromarray(csiFrame)
        csiFilename = "CSI_" + fileTime
        csiImage.save(os.path.join(self.calibration_dir, csiFilename))
        zedFilename = ""
        if ZED_ENABLED:
            self.zedFrameLock.acquire()
            zedFrame = cv2.cvtColor(self.zedStreamer.lastFrame, cv2.COLOR_BGR2RGB)
            self.zedFrameLock.release()
            zedImage = Image.fromarray(zedFrame)
            zedFilename = "ZED_" + fileTime
            zedImage.save(os.path.join(self.calibration_dir, zedFilename))

        cherrypy.response.headers['Content-Type'] = 'text/markdown'
        return simplejson.dumps(dict(csiFilename=csiFilename, zedFilename=zedFilename))

    @cherrypy.expose
    def intrinsics(self):
        return self.template.intrinsics(ZED_ENABLED)

    @cherrypy.expose
    def index(self):
        if self.csiStatus == True and self.zedStatus == True:
            raise cherrypy.HTTPRedirect("/data")
        msg = "<h1>Error</h1>"
        if self.zedStatus == False:
            msg += "ZED Depth Camera not detected or <code>pyzed</code> not installed.<br>"
        if self.csiStatus == False:
            msg += "Mono camera not detected.<br>"
        msg += "Please connect the missing camera(s), install the <code>pyzed</code> SDK, and restart the server." \
        " You can still choose to record data from the available cameras, view files, or read the documentation."
        return self.template.index(msg)