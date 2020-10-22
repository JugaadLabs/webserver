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

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage

from src.barcode_scanner import BarcodeScanner
from src.templates import Templates

class BarcodeHandler(object):
    def __init__(self, csiStreamer):
        self.templates = Templates()
        self.scanner = BarcodeScanner(timeout=500)
        self.csiStreamer = csiStreamer
        self.previewResolution = (480,427)

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
        if detectedCount == 0:
            text = "No barcodes or data matrices detected"
        else:
            text = "<table class=\"table\"><thead><th>Type</th><th>Data</th></thead><tbody>"
            for scan in dm_scans:
                text+= "<tr><td>%s</td><td>%s</td></tr>" % ("ECC200", scan)
            for scan in barcode_scans:
                text+= "<tr><td>%s</td><td>%s</td></tr>" % (scan[1], scan[0])
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
            resized = cv2.resize(barcodeImage, self.previewResolution, cv2.INTER_AREA)
            # TODO: insert barcode reading code here
            (flag, encodeImage) = cv2.imencode(".jpg", resized)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +  bytearray(encodeImage) + b'\r\n')
        print("Shutting down!")

    @cherrypy.expose
    def index(self):
        return self.templates.barcode()

    @cherrypy.expose
    def ws(self):
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))
