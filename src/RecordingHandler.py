from cherrypy.lib.static import serve_file
import os
import signal
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
import numpy as np
import re

from src.CameraState import CameraState
from src.CSIStreamer import CSIStreamer
from src.templates import Templates

ZED_ENABLED = True

try:
    import pyzed.sl as sl
except ImportError as e:
    cherrypy.log("pyzed not available! Using V4L2 fallback.")
    ZED_ENABLED = False
else:
    from src.ZEDStreamer import ZEDStreamer


class RecordingHandler(object):
    def __init__(self, recording_dir, csiStreamer, zedStreamer, csiStatus, zedStatus, mode, previewResolution, zedPreviewResolution):
        self.previewResolution = previewResolution
        self.zedPreviewResolution = zedPreviewResolution
        self.recording_dir = os.path.abspath(recording_dir)
        self.calibration_dir = os.path.join(self.recording_dir, "calibration")
        Path(self.calibration_dir).mkdir(parents=True, exist_ok=True)

        self.template = Templates()
        self.HD_STREAMING = False
        self.DETECTORS_ENABLED = True if mode == 0 else False

        self.csiStatus = csiStatus
        self.zedStatus = zedStatus
        global ZED_ENABLED
        if zedStatus == False:
            ZED_ENABLED = False

        self.csiStreamer = csiStreamer
        self.currentCSIFrame = np.zeros((512, 512, 3))
        self.currentZEDFrame = np.zeros((512, 512, 3))
        self.currentCalibrationText = "Using default values for H and L0"

        cherrypy.engine.subscribe("hdResolution", self.getCurrentResolution)
        cherrypy.engine.subscribe("csiFrame", self.updateCSIFrame)
        cherrypy.engine.subscribe(
            "calibrationResult", self.calibrationResultCallback)
        self.calibrationResult = "Calibration failed."
        if ZED_ENABLED:
            self.zedStreamer = zedStreamer
            cherrypy.engine.subscribe("zedFrame", self.updateZEDFrame)

    def getCurrentResolution(self, HD):
        self.HD_STREAMING = HD

    def setResolution(self):
        if self.HD_STREAMING:
            cherrypy.engine.publish("hdResolution", False)

    def calibrationResultCallback(self, calibrationResult):
        error = calibrationResult[0]
        H = calibrationResult[1]
        l0 = calibrationResult[2]
        if error == 0:
            self.calibrationResult = "Calibration Successful! Parameters are: H=%f, L0=%f" % (
                H, l0)
            self.calibrationResult = "Using Parameters H=%f, L0=%f" % (H, l0)
            cherrypy.engine.publish(
                "changeSetting", 'params["detectionHandler"]["H"]', H)
            cherrypy.engine.publish(
                "changeSetting", 'params["detectionHandler"]["L0"]', l0)
        else:
            self.calibrationResult = "Calibration failed. Please try retaking CSI_%d.jpeg, making sure the person is standing at the correct position." % (
                -error)

    def updateCSIFrame(self, frame):
        self.currentCSIFrame = frame

    def updateZEDFrame(self, frame):
        self.currentZEDFrame = frame

    def camera_handler(self, streamer, command, t):
        if command == CameraState.RECORD:
            streamer.startRecording(t)
        elif command == CameraState.STOP:
            streamer.stopRecording()

    def getCurrentStatusText(self, isRecording, filename):
        if isRecording == True:
            return " is recording to " + filename + "."
        elif isRecording == False:
            return " file saved to " + filename + "."

    def commandHandler(self, csi, zed, command):
        t = datetime.datetime.now()
        if csi:
            self.camera_handler(self.csiStreamer, command, t)
        if zed and ZED_ENABLED:
            self.camera_handler(self.zedStreamer, command, t)

    def getCameraStatus(self):
        csiFilename = self.csiStreamer.recorder.filename
        if csiFilename == "":
            csiText = "Mono Camera is streaming."
        else:
            csiText = "Mono Camera " + \
                self.getCurrentStatusText(
                    self.csiStreamer.isRecording(), csiFilename)
        if ZED_ENABLED:
            zedFilename = self.zedStreamer.filename
            if zedFilename == "":
                zedText = "ZED Depth Camera is streaming."
            else:
                zedText = "ZED Depth Camera " + \
                    self.getCurrentStatusText(
                        self.zedStreamer.isRecording(), zedFilename)
        else:
            zedText = "pyzed not installed or ZED Depth Camera not connected. ZED Recording disabled."
        return csiText, zedText

    @cherrypy.expose
    def stream(self):
        cherrypy.response.headers['Content-Type'] = "multipart/x-mixed-replace; boundary=frame"
        return self.getFrame()
    stream._cp_config = {'response.stream': True}

    @cherrypy.expose
    def shutdown(self):
        cherrypy.engine.publish('shutdown')
        time.sleep(3)
        cherrypy.engine.exit()
        os.kill(os.getpid(), signal.SIGQUIT)
        # return "Shutting down webserver!"

    def getFrame(self):
        while True:
            state = cherrypy.engine.state
            if state == cherrypy.engine.states.STOPPING or state == cherrypy.engine.states.STOPPED:
                break
            frame = self.currentCSIFrame
            if frame is None:
                continue
            resized = cv2.resize(frame, self.previewResolution, cv2.INTER_AREA)
            (flag, encodeImage) = cv2.imencode(".jpg", resized)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodeImage) + b'\r\n')
        cherrypy.log("Shutting down!")
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
            frame = self.currentZEDFrame
            if frame is None:
                continue
            resized = cv2.resize(
                frame, self.zedPreviewResolution, cv2.INTER_AREA)
            (flag, encodeImage) = cv2.imencode(".jpg", resized)
            if flag:
                yield(b'--zedframe\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodeImage) + b'\r\n')
        cherrypy.log("Shutting down ZED!")

    @cherrypy.expose
    def camerastatus(self):
        csiText, zedText = self.getCameraStatus()
        cherrypy.response.headers['Content-Type'] = 'text/markdown'
        return simplejson.dumps(dict(csi=csiText, zed=zedText))

    @cherrypy.expose
    def calibrationstatus(self):
        cherrypy.response.headers['Content-Type'] = 'text/markdown'
        return self.currentCalibrationText

    @cherrypy.expose
    def download(self, filepath):
        return serve_file(filepath, "application/x-download", "attachment")

    def executeAction(self, csi, zed, action):
        csi = True if csi == 'true' else False
        zed = True if zed == 'true' else False
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
        self.setResolution()
        return self.template.data(ZED_ENABLED)

    @cherrypy.expose
    def clearAll(self):
        files = os.listdir(self.calibration_dir)
        r = re.compile('[0-9]_CSI.*')
        calibrationFiles = list(filter(r.match, files))
        if calibrationFiles is not None:
            calibrationFiles = [os.path.join(
                self.calibration_dir, x) for x in calibrationFiles]
        else:
            return "No files for calibration have been saved yet."
        for filename in calibrationFiles:
            os.remove(filename)
        return "Distance calibration images deleted."

    @cherrypy.expose
    def calibrateDistance(self):
        files = os.listdir(self.calibration_dir)
        r = re.compile('[0-9]_CSI.*')
        calibrationFiles = list(filter(r.match, files))
        if calibrationFiles is not None:
            calibrationFiles = [os.path.join(
                self.calibration_dir, x) for x in calibrationFiles]
        else:
            return "Images missing. Please record images for each distance before starting distance calibration."
        if len(calibrationFiles) < 8:
            return "Insufficient images to start calibration. Please record images for each distance before starting distance calibration."
        calibrationFiles.sort()
        cherrypy.engine.publish("distanceCalibrationFiles", calibrationFiles)
        return self.calibrationResult

    @cherrypy.expose
    def captureImage(self, csiFilename="", zedFilename=""):
        cherrypy.log(csiFilename, zedFilename)
        now = datetime.datetime.now()
        fileTime = now.strftime("IMG_%Y-%m-%d-%H-%M-%S")+".jpeg"
        csiFilename = csiFilename + "_CSI.jpeg" if csiFilename is not "" else "CSI_" + fileTime
        csiFrame = self.currentCSIFrame
        csiFrame = cv2.cvtColor(csiFrame, cv2.COLOR_BGR2RGB)
        csiImage = Image.fromarray(csiFrame)
        csiImage.save(os.path.join(self.calibration_dir, csiFilename))

        if ZED_ENABLED:
            zedFrame = self.currentZEDFrame
            zedFrame = cv2.cvtColor(zedFrame, cv2.COLOR_BGR2RGB)
            zedImage = Image.fromarray(zedFrame)
            zedFilename = zedFilename + "_ZED.jpeg" if zedFilename is not "" else "ZED_" + fileTime
            zedImage.save(os.path.join(self.calibration_dir, zedFilename))
        else:
            zedFilename = ""

        cherrypy.response.headers['Content-Type'] = 'text/markdown'
        return simplejson.dumps(dict(csiFilename=csiFilename, zedFilename=zedFilename))

    @cherrypy.expose
    def calibration(self):
        self.setResolution()
        return self.template.calibration(ZED_ENABLED, self.DETECTORS_ENABLED)

    @cherrypy.expose
    def index(self):
        if self.csiStatus == True and self.zedStatus == True:
            raise cherrypy.HTTPRedirect("/data")
        header = ""
        msg = ""
        if self.zedStatus == False:
            header = "<h2>No ZED Camera connected</h2>"
            msg += "ZED Depth Camera not detected or <code>pyzed</code> not installed.<br>"
        if self.csiStatus == False:
            header = "<h2>Error</h2>"
            msg += "Mono camera not detected.<br>"
        msg += "Please connect the missing camera(s), install the <code>pyzed</code> SDK, and restart the server." \
            " Click on the sidebar to record data from the available cameras, view files, or read the documentation."
        return self.template.index(header+msg)
