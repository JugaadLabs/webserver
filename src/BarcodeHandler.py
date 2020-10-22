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

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage

from src.barcode_scanner import BarcodeScanner
from src.templates import Templates


class BarcodeHandler(object):
    def __init__(self, csiStreamer, dir):
        self.templates = Templates()
        self.scanner = BarcodeScanner(timeout=500)
        self.csiStreamer = csiStreamer
        self.previewResolution = (480, 427)
        self.recordingResolution = (960, 854)
        self.RECORDING = False
        self.filename = ""
        self.dir = dir
        self.barcodeData = []
        self.currentStatus = "Press the Record button to record a video of barcode detections"

    def sendWebsocketMessage(self, txt):
        cherrypy.engine.publish('websocket-broadcast', TextMessage(txt))

    def updateScan(self, image):
        self.scanner.readImage(image)
        self.scanner.grayscaleStats()
        self.scanner.decodeBarcodes()
        self.scanner.drawBbox()
        dm_scans = self.scanner.dms_list
        barcode_scans = self.scanner.bcs_list
        detectedCount = len(dm_scans)+len(barcode_scans)
        if self.RECORDING:
            self.recordData()
        if detectedCount == 0:
            text = "No barcodes or data matrices detected"
        else:
            text = "<table class=\"table\"><thead><th>ID</th><th>Data</th><th>Type</th></thead><tbody>"
            for scan in dm_scans:
                text += "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    scan[0], scan[1], scan[2])
            for scan in barcode_scans:
                text += "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    scan[0], scan[1], scan[2])
            text += "</tbody></table><br>%d barcodes/data-matrices detected" % detectedCount
        self.sendWebsocketMessage(text)

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
            frame = self.csiStreamer.getBarcodeFrame()
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
        print("Shutting down!")

    @cherrypy.expose
    def index(self):
        return self.templates.barcode()

    @cherrypy.expose
    def ws(self):
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))

    @cherrypy.expose
    def record(self):
        return self.startRecording()

    @cherrypy.expose
    def stop(self):
        return self.stopRecording()

    @cherrypy.expose
    def barcodeStatus(self):
        return self.currentStatus

    def recordData(self):
        timestamp = time.time()
        dataDict = {
            "barcodes": self.scanner.bcs_list,
            "data_matrices": self.scanner.dms_list,
            "timestamp": timestamp
        }
        videoFrame = cv2.resize(
            self.scanner.image, self.recordingResolution, cv2.INTER_AREA)
        self.out.write(videoFrame)
        self.barcodeData.append(dataDict)

    def startRecording(self):
        if self.RECORDING is False:
            startTime = datetime.datetime.now()
            self.filename = startTime.strftime("BARCODE_%Y-%m-%d-%H-%M-%S")
            print("Recording to - " + self.filename)
            self.RECORDING = True
            filepath = os.path.join(self.dir, self.filename+".avi")
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.out = cv2.VideoWriter(
                filepath, fourcc, 30.0, self.recordingResolution)
            self.barcodeData = []
        return self.filename

    def stopRecording(self):
        if self.RECORDING is True:
            self.RECORDING = False
            print("Stopped recording to - " + self.filename)
            filepath = os.path.join(self.dir, self.filename+".pkl")
            with open(filepath, 'wb') as f:
                pickle.dump(self.barcodeData, f)
            self.out.release()
        return "Stopped recording lah!"