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

from src.templates import Templates

TENSORRT_ENABLED = True
try:
    from src.trig_distance import monoDistance
except ImportError as e:
    print("TensorRT and/or PyCuda not available!")
    TENSORRT_ENABLED = False
else:
    print("Loading TensorRT and PyCuda modules")
    from src.trig_distance import monoDistance

class DetectionHandler(object):
    def __init__(self, csiStreamer):
        self.templates = Templates()
        self.csiStreamer = csiStreamer

    def sendWebsocketMessage(self, txt):
        cherrypy.engine.publish('websocket-broadcast', TextMessage(txt))

    def updateScan(self, image):
        text = "Placeholder"
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
            frame = self.csiStreamer.getCurrentFrame()
            if frame is None:
                continue
            self.updateScan(frame)
            # TODO: change with real code
            image = frame
            resized = cv2.resize(image, (int(0.5*image.shape[1]), int(0.5*image.shape[0])), cv2.INTER_AREA)
            (flag, encodeImage) = cv2.imencode(".jpg", resized)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +  bytearray(encodeImage) + b'\r\n')
        print("Shutting down!")

    @cherrypy.expose
    def index(self):
        return self.templates.detection()

    @cherrypy.expose
    def ws(self):
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))
