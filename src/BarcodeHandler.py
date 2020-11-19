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
import pickle
import numpy as np

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage

from src.barcode_scanner import BarcodeScanner
from src.templates import Templates
from src.CSIRecorder import CSIRecorder


class BarcodeHandler(object):
    def __init__(self, dir, crop, timeout, previewResolution, recordingResolution):
        self.templates = Templates()

        framerate = 1000/timeout
        self.scanner = BarcodeScanner(timeout=timeout)
        self.recorder = CSIRecorder(dir, recordingResolution, framerate, "BARCODE")

        self.previewResolution = previewResolution
        self.filename = ""
        self.dir = dir
        self.barcodeData = []
        self.currentStatus = "Press the Record button to record a video of barcode detections."
        self.currentBarcodeFrame = np.zeros((512, 512, 3))
        self.crop = crop
        cherrypy.engine.subscribe("csiFrame", self.updateFrame)

    def updateFrame(self, frame):
        if frame is None:
            return
        h = frame.shape[0]
        w = frame.shape[1]
        h_low = self.crop[0]
        h_high = self.crop[1]
        w_low = self.crop[2]
        w_high = self.crop[3]
        # fallback if the crop is unreasonable
        if h_low < 0 or w_low < 0 or h_high > h or w_high > w:
            h_low = h//4
            h_high = 3*h//4
            w_low = 0
            w_high = w-1
        self.currentBarcodeFrame = frame[h_low:h_high, w_low:w_high, :].copy()

    def sendWebsocketMessage(self, txt):
        cherrypy.engine.publish('websocket-broadcast', TextMessage("BAR"+txt))

    def updateScan(self, image):
        self.scanner.readImage(image)
        self.scanner.grayscaleStats()
        self.scanner.decodeBarcodes()
        self.scanner.drawBbox()
        dm_scans = self.scanner.dms_list
        barcode_scans = self.scanner.bcs_list
        detectedCount = len(dm_scans)+len(barcode_scans)

        if self.recorder.RECORDING:
            timestamp = time.time()
            dataDict = {
                "barcodes": self.scanner.bcs_list,
                "data_matrices": self.scanner.dms_list,
                "timestamp": timestamp
            }
            self.recorder.recordData(self.scanner.image, dataDict)

        if detectedCount == 0:
            html = "No barcodes or data matrices detected"
        else:
            html = "<table class=\"table\"><thead><th>ID</th><th>Data</th><th>Type</th></thead><tbody>"
            for scan in dm_scans:
                html += "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    scan[0], scan[1], scan[2])
            for scan in barcode_scans:
                html += "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    scan[0], scan[1], scan[2])
            html += "</tbody></table><br>%d barcodes/data-matrices detected" % detectedCount
        self.sendWebsocketMessage(html)

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
            frame = self.currentBarcodeFrame
            if frame is None:
                continue
            self.updateScan(frame)
            barcodeImage = self.scanner.image
            resized = cv2.resize(
                barcodeImage, self.previewResolution, cv2.INTER_AREA)
            # TODO: insert barcode reading code here
            (flag, encodeImage) = cv2.imencode(".jpg", resized)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodeImage) + b'\r\n')
        cherrypy.log("Shutting down!")

    @cherrypy.expose
    def index(self):
        return self.templates.barcode()

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
    def sd(self):
        cherrypy.engine.publish("hdResolution", False)
        return self.status()

    @cherrypy.expose
    def hd(self):
        cherrypy.engine.publish("hdResolution", True)
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