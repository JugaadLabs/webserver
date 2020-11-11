import cv2
from cherrypy.process import plugins
import netifaces as ni
from pathlib import Path
import os
import sys
import string
import subprocess
import time
import traceback
import threading
import cherrypy
import jinja2
import multiprocessing

from settings import params

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage

from src.FilesHandler import FilesHandler
from src.RecordingHandler import RecordingHandler
from src.BarcodeHandler import BarcodeHandler
from src.TestHandler import TestHandler
from src.CSIStreamer import CSIStreamer
from src.DocuHandler import DocuHandler
from src.WebSocketHandler import WebSocketHandler
from src.DetectionHandler import DetectionHandler

ZED_ENABLED = True
try:
    import pyzed.sl as sl
except ImportError as e:
    print("pyzed not available! Using V4L2 fallback.")
    ZED_ENABLED = False
else:
    print("Loading ZED Streaming thread")
    from src.ZEDStreamer import ZEDStreamer


def testCamera(camId):
    cap = cv2.VideoCapture(camId)
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if w == 0 or h == 0 or w/h > 3:
        return -1
    return camId
    cap.release()


def selfTest():
    ret0 = testCamera(0)
    ret1 = testCamera(1)

    csi = max(ret0, ret1)

    zed = False
    if ZED_ENABLED:
        cam = sl.Camera()
        status = cam.open()
        if status == sl.ERROR_CODE.SUCCESS:
            cam.close()
            zed = True
    return csi, zed


class Server(object):
    def run(self, host="127.0.0.1", port=8000, dir='.', csiDevice=-1):
        dir = os.path.abspath(dir)
        Path(dir).mkdir(parents=True, exist_ok=True)
        print("Recording to: " + dir)
        CP_CONF = {
            '/vendor': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': os.path.abspath('./vendor')
            },
            '/css': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': os.path.abspath('./css')
            },
            '/webfonts': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': os.path.abspath('./webfonts')
            },
            '/ws': {
                'tools.websocket.on': True,
                'tools.websocket.handler_cls': WebSocketHandler
            }
        }

        cherrypy.config.update({
            'server.socket_host': host,
            'server.socket_port': port,
        })

        zedStatus = False
        if csiDevice == -1:
            csiDevice, zedStatus = selfTest()
        else:
            _, zedStatus = selfTest()

        csiStatus = True if csiDevice != -1 else False

        csiFrameLock = threading.Lock()
        csiStreamer = CSIStreamer(csiFrameLock, dir, params["csiStreamer"]["recordingInterval"], csiDevice, params["csiStreamer"]
                                  ["stdResolution"], params["csiStreamer"]["hdResolution"], params["csiStreamer"]["recordingResolution"], params["csiStreamer"]["framerate"])
        # threading.Thread(None, csiStreamer.run).start()

        zedFrameLock = None
        zedStreamer = None

        if ZED_ENABLED:
            zedFrameLock = threading.Lock()
            zedStreamer = ZEDStreamer(zedFrameLock, dir, params["zedStreamer"]["recordingInterval"], params["zedStreamer"]
                                      ["resolution"], params["zedStreamer"]["depth"], params["zedStreamer"]["framerate"])
            zedStreamThread = threading.Thread(
                None, zedStreamer.run, daemon=True)
            zedStreamThread.start()

        WebSocketPlugin(cherrypy.engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()

        cherrypy.tree.mount(RecordingHandler(
            dir, csiStreamer, zedStreamer, csiStatus, zedStatus, params["recordingHandler"]["previewResolution"], params["recordingHandler"]["zedPreviewResolution"]), '/', config=CP_CONF)
        cherrypy.tree.mount(BarcodeHandler(dir, params["barcodeHandler"]["crop"], params["barcodeHandler"]["timeout"], params["barcodeHandler"]["previewResolution"], params["barcodeHandler"]["recordingResolution"]),
                            '/barcode', config=CP_CONF)
        cherrypy.tree.mount(DetectionHandler(
            dir, params["detectionHandler"]["framerate"], params["detectionHandler"]["recordingResolution"]), '/detection', config=CP_CONF)
        cherrypy.tree.mount(FilesHandler(dir), '/files', config=CP_CONF)
        cherrypy.tree.mount(TestHandler(), '/test')
        cherrypy.tree.mount(DocuHandler(), '/documentation', config=CP_CONF)
        cherrypy.engine.start()
        cherrypy.engine.block()


def main():
    server = Server()
    if len(sys.argv) == 5:
        ip = ni.ifaddresses(sys.argv[1])[ni.AF_INET][0]['addr']
        server.run(ip, int(sys.argv[2]), sys.argv[3], int(sys.argv[4]))
    if len(sys.argv) == 4:
        ip = ni.ifaddresses(sys.argv[1])[ni.AF_INET][0]['addr']
        server.run(ip, int(sys.argv[2]), sys.argv[3])
    if len(sys.argv) == 3:
        ip = ni.ifaddresses(sys.argv[1])[ni.AF_INET][0]['addr']
        server.run(ip, int(sys.argv[2]))
    if len(sys.argv) == 2:
        ip = ni.ifaddresses(sys.argv[1])[ni.AF_INET][0]['addr']
        server.run(ip)
    else:
        ip = ni.ifaddresses('lo')[ni.AF_INET][0]['addr']
        server.run(ip)


if __name__ == "__main__":
    main()
