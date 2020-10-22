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
from src.zmq_utils import zmqNode

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
    from src.uilts.uilts import detection_class_name_3cls


class DetectionHandler(object):
    def __init__(self, csiStreamer, enginePath):
        self.templates = Templates()
        self.csiStreamer = csiStreamer

        if TENSORRT_ENABLED:
            self.inputResolution = (480, 640)
            self.currentDetectionFrame = np.zeros(
                (self.inputResolution[0], self.inputResolution[1], 3))
            self.currentBirdsEyeFrame = np.zeros((480, 480, 3))
            self.sendImgNode = zmqNode('send', 9500)
            self.recvResultsNode = zmqNode('recv', 9501)
            self.selectedBboxes = None
            self.bboxDistances = None

    def sendWebsocketMessage(self, txt):
        cherrypy.engine.publish('websocket-broadcast', TextMessage(txt))

    def updateDetections(self):
        image = self.csiStreamer.getCurrentFrame()
        if image is None:
            return
        resized = cv2.resize(
            image, (self.inputResolution), cv2.INTER_AREA)
        self.sendImgNode.send_array(resized)
        self.currentDetectionFrame, self.currentBirdsEyeFrame, self.selectedBboxes, self.bboxDistances = self.recvResultsNode.recv_zipped_pickle()
        # text = "Placeholder"
        # self.sendWebsocketMessage(text)

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
        print("Shutting down!")

    def getDetectionFrame(self):
        while True:
            state = cherrypy.engine.state
            if state == cherrypy.engine.states.STOPPING or state == cherrypy.engine.states.STOPPED:
                break
            self.updateDetections()
            image = self.currentDetectionFrame
            (flag, encodeImage) = cv2.imencode(".jpg", image)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodeImage) + b'\r\n')
        print("Shutting down!")

    @cherrypy.expose
    def index(self):
        return self.templates.detection(TENSORRT_ENABLED)

    @cherrypy.expose
    def ws(self):
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))
