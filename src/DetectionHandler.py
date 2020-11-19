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
import numpy as np
from pathlib import Path
from operator import itemgetter
import multiprocessing

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage

from src.templates import Templates
from src.CSIRecorder import CSIRecorder


TENSORRT_ENABLED = True
try:
    from src.trig_distance import monoDistance
    from src.DetectionProcess import detectionProcessFunction
except ImportError as e:
    print("TensorRT and/or PyCuda not available!")
    TENSORRT_ENABLED = False
else:
    print("Loading TensorRT and PyCuda modules")
    from src.trig_distance import monoDistance
    from src.uilts.uilts import detection_class_name_3cls, detection_class_name_8cls


class DetectionHandler(object):
    def __init__(self, dir, framerate, recordingResolution, enginePath, H, L0):
        self.templates = Templates()
        self.HD_STREAMING = False
        if TENSORRT_ENABLED:
            cherrypy.engine.subscribe(
                "hdResolution", self.getCurrentResolution)
            self.inputResolution = (480, 640)
            self.currentDetectionFrame = np.zeros(
                (self.inputResolution[0], self.inputResolution[1], 3))
            self.currentBirdsEyeFrame = np.zeros((480, 480, 3))
            self.selectedBboxes = np.array([])
            self.bboxDistances = np.array([])
            self.recorder = CSIRecorder(
                dir, recordingResolution, framerate, "DETECTION")
            self.currentStatus = "Press the Record button to record a video of object detections"
            try:
                multiprocessing.set_start_method('spawn')
            except RuntimeError:
                pass
            self.sendQueue = multiprocessing.Queue(maxsize=5)
            self.recvQueue = multiprocessing.Queue(maxsize=5)
            self.recvListQueue = multiprocessing.Queue(maxsize=1)
            self.sendListQueue = multiprocessing.Queue(maxsize=1)
            p = multiprocessing.Process(target=detectionProcessFunction, args=(
                enginePath, self.recvQueue, self.sendQueue, self.recvListQueue, self.sendListQueue, H, L0, dir))
            p.start()
            cherrypy.engine.subscribe("csiFrame", self.updateDetections)
            cherrypy.engine.subscribe(
                "distanceCalibrationFiles", self.calibrateDistance)

    def getCurrentResolution(self, HD):
        self.HD_STREAMING = HD

    def setResolution(self):
        if self.HD_STREAMING:
            cherrypy.engine.publish("hdResolution", False)

    def calibrateDistance(self, distanceCalibrationFiles):
        cherrypy.engine.unsubscribe("csiFrame", self.updateDetections)
        cherrypy.log("Sending calibration files: ", distanceCalibrationFiles)
        self.sendListQueue.put(distanceCalibrationFiles)
        # timeout if not done in time
        i = 0
        while self.recvListQueue.empty() and i < 10:
            time.sleep(0.1)
            i += 1
        if not self.recvListQueue.empty():
            data = self.recvListQueue.get()
            calibrationResult = data
            cherrypy.log("Calibrated Values", calibrationResult)
            if type(calibrationResult) is list:
                cherrypy.engine.publish("calibrationResult", calibrationResult)
        else:
            cherrypy.log("Timed out waiting for response for detector.")
        cherrypy.engine.subscribe("csiFrame", self.updateDetections)

    def sendWebsocketMessage(self, txt):
        cherrypy.engine.publish('websocket-broadcast', TextMessage("DET"+txt))

    def updateDetections(self, image):
        if image is None or type(image) is not np.ndarray:
            return
        resized = cv2.resize(
            image, (self.inputResolution), cv2.INTER_AREA)

        self.sendQueue.put(resized)
        while not self.recvQueue.empty():
            detectionsDict = self.recvQueue.get()
            self.currentDetectionFrame = detectionsDict['img']
            self.currentBirdsEyeFrame = detectionsDict['birdsView']
            self.selectedBboxes = detectionsDict['selectedBboxes']
            self.bboxDistances = detectionsDict['bboxDistances']

            if self.recorder.RECORDING:
                timestamp = time.time()
                dataDict = {
                    "bboxes": self.selectedBboxes,
                    "distances": self.bboxDistances,
                    "timestamp": timestamp
                }
                self.recorder.recordData(self.currentDetectionFrame, dataDict)

            detectedCount = len(self.selectedBboxes)
            if detectedCount == 0:
                html = "No objects detected."
            else:
                html = "<table class=\"table\"><thead><th>Object</th><th>X</th><th>Y</th></thead><tbody>"
                for i in range(detectedCount):
                    distance = self.bboxDistances[i]
                    bbox = self.selectedBboxes[i]
                    className = detection_class_name_8cls[int(bbox[5])]
                    X = distance[0]
                    Y = distance[1]
                    html += "<tr><td>%s</td><td>%.2f m</td><td>%.2f m</td></tr>" % (
                        className, X, Y)
                html += "</tbody></table>"
            self.sendWebsocketMessage(html)

    @cherrypy.expose
    def detectionStream(self):
        cherrypy.response.headers['Content-Type'] = "multipart/x-mixed-replace; boundary=frame"
        return self.getDetectionFrame()
    detectionStream._cp_config = {'response.stream': True}

    @cherrypy.expose
    def birdeyeStream(self):
        cherrypy.response.headers['Content-Type'] = "multipart/x-mixed-replace; boundary=frame"
        return self.getBirdsEyeFrame()
    birdeyeStream._cp_config = {'response.stream': True}

    def getBirdsEyeFrame(self):
        while True:
            state = cherrypy.engine.state
            if state == cherrypy.engine.states.STOPPING or state == cherrypy.engine.states.STOPPED:
                break
            image = self.currentBirdsEyeFrame
            (flag, encodeImage) = cv2.imencode(".jpg", image)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodeImage) + b'\r\n')
        cherrypy.log("Shutting down!")

    def getDetectionFrame(self):
        while True:
            state = cherrypy.engine.state
            if state == cherrypy.engine.states.STOPPING or state == cherrypy.engine.states.STOPPED:
                break
            image = self.currentDetectionFrame
            (flag, encodeImage) = cv2.imencode(".jpg", image)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodeImage) + b'\r\n')
        cherrypy.log("Shutting down!")

    @cherrypy.expose
    def index(self):
        self.setResolution()
        return self.templates.detection(TENSORRT_ENABLED)

    @cherrypy.expose
    def ws(self):
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))

    @cherrypy.expose
    def record(self):
        self.recorder.startRecording()
        return self.status()

    @cherrypy.expose
    def stop(self):
        self.recorder.stopRecording()
        return self.status()

    @cherrypy.expose
    def status(self):
        filename = self.recorder.filename
        if filename != "":
            if self.recorder.RECORDING:
                self.currentStatus = "Recording to: " + filename
            else:
                self.currentStatus = "Saved recording to: " + filename
        return self.currentStatus
