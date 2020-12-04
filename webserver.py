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
import fileinput

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
from src.DisabledHandler import DisabledHandler

ZED_ENABLED = True
try:
    import pyzed.sl as sl
except ImportError as e:
    cherrypy.log("pyzed not available! Using V4L2 fallback.")
    ZED_ENABLED = False
else:
    cherrypy.log("Loading ZED Streaming thread")
    from src.ZEDStreamer import ZEDStreamer


def testCamera(camId):
    cap = cv2.VideoCapture(camId)
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    cap.release()
    if w == 0 or h == 0 or w/h > 3:
        return -1
    return camId


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
    def run(self, host="127.0.0.1", port=8000, dir='.', mode=0, csiDevice=-1):
        dir = os.path.abspath(dir)
        Path(dir).mkdir(parents=True, exist_ok=True)
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
        accessLogFile = os.path.join(os.getcwd(), "access.log")
        errorLogFile = os.path.join(os.getcwd(), "error.log")
        cherrypy.config.update({
            'server.socket_host': host,
            'server.socket_port': port,
            'engine.autoreload.on': False,
            'log.error_file': errorLogFile,
            'log.access_file': accessLogFile
        })
        cherrypy.log("Recording to: " + dir)

        zedStatus = False
        if csiDevice == -1:
            csiDevice, zedStatus = selfTest()
        else:
            _, zedStatus = selfTest()

        csiStatus = True if csiDevice != -1 else False

        csiStreamer = CSIStreamer(dir, params["csiStreamer"]["recordingInterval"], csiDevice, params["csiStreamer"]
                                  ["stdResolution"], params["csiStreamer"]["hdResolution"], params["csiStreamer"]["recordingResolution"], params["csiStreamer"]["framerate"])
        # threading.Thread(None, csiStreamer.run).start()

        zedStreamer = None

        if ZED_ENABLED:
            zedFrameLock = threading.Lock()
            zedStreamer = ZEDStreamer(dir, params["zedStreamer"]["recordingInterval"], params["zedStreamer"]
                                      ["resolution"], params["zedStreamer"]["depth"], params["zedStreamer"]["framerate"])
            zedStreamThread = threading.Thread(
                None, zedStreamer.run, daemon=True)
            zedStreamThread.start()

        WebSocketPlugin(cherrypy.engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()
        cherrypy.tree.mount(RecordingHandler(
            dir, csiStreamer, zedStreamer, csiStatus, zedStatus, mode, params["recordingHandler"]["previewResolution"], params["recordingHandler"]["zedPreviewResolution"]), '/', config=CP_CONF)
        if mode == 0:
            cherrypy.log("All modules enabled")
            cherrypy.tree.mount(BarcodeHandler(dir, params["barcodeHandler"]["crop"], params["barcodeHandler"]["timeout"], params["barcodeHandler"]["previewResolution"], params["barcodeHandler"]["recordingResolution"]),
                                '/barcode', config=CP_CONF)
            cherrypy.tree.mount(DetectionHandler(
                dir, params["detectionHandler"]["framerate"], params["detectionHandler"]["recordingResolution"], params["detectionHandler"]["enginepath"], params["detectionHandler"]["H"], params["detectionHandler"]["L0"]), '/detection', config=CP_CONF)
        else:
            cherrypy.log("Barcode detection and object detection disabled.")
            cherrypy.tree.mount(DisabledHandler(),
                                '/barcode', config=CP_CONF)
            cherrypy.tree.mount(DisabledHandler(),
                                '/detection', config=CP_CONF)

        cherrypy.tree.mount(FilesHandler(dir), '/files', config=CP_CONF)
        cherrypy.tree.mount(TestHandler(), '/test')
        cherrypy.tree.mount(DocuHandler(), '/documentation', config=CP_CONF)
        cherrypy.engine.start()
        cherrypy.engine.block()


def changeSetting(key, value):
    # key = kv[0]
    # value = kv[1]
    for line in fileinput.input(os.path.join(os.getcwd(), "settings.py"), inplace=True):
        if key in line:
            print(key + " = " + str(value), end='\n')
        else:
            print(line, end='')


def get_ip_address(interface):
    print('Waiting for interface to come online')
    timeout = 120
    for i in range(timeout):
        print("Waiting %d/%d seconds\r"%(i,timeout),end='')
        if ni.AF_INET in ni.ifaddresses(interface):
            return ni.ifaddresses(interface)[ni.AF_INET][0]['addr']
        time.sleep(1)
    return None


def main():
    server = Server()
    cherrypy.engine.subscribe("changeSetting", changeSetting)
    ipaddr = None
    if len(sys.argv) > 1:
        ipaddr = get_ip_address(sys.argv[1])
        if ipaddr is None:
            print('Interface not online, shutting down')
            return
        print('Interface %s online. Your IP is %s.' % (sys.argv[1], ipaddr))
    if len(sys.argv) == 6:
        server.run(ipaddr, int(sys.argv[2]), sys.argv[3],
                   int(sys.argv[4]), int(sys.argv[5]))
    if len(sys.argv) == 5:
        server.run(ipaddr, int(sys.argv[2]), sys.argv[3], int(sys.argv[4]))
    if len(sys.argv) == 4:
        server.run(ipaddr, int(sys.argv[2]), sys.argv[3])
    if len(sys.argv) == 3:
        server.run(ipaddr, int(sys.argv[2]))
    if len(sys.argv) == 2:
        server.run(ipaddr)
    else:
        ipaddr = get_ip_address('lo')
        server.run(ipaddr)


if __name__ == "__main__":
    main()
