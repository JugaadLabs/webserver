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

from src.barcode_scanner import BarcodeScanner
from src.templates import Templates

class BarcodeHandler(object):
    def __init__(self, csiStreamer):
        self.templates = Templates()
        self.scanner = BarcodeScanner(timeout=500)
        self.csiStreamer = csiStreamer

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
            frame = self.csiStreamer.getCurrentFrame()
            if frame is None:
                continue
            resized = cv2.resize(frame, (int(0.5*frame.shape[1]), int(0.5*frame.shape[0])), cv2.INTER_AREA)
            # TODO: insert barcode reading code here
            (flag, encodeImage) = cv2.imencode(".jpg", resized)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +  bytearray(encodeImage) + b'\r\n')
        print("Shutting down!")

    @cherrypy.expose
    def index(self):
        return self.templates.barcode()