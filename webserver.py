import os
import sys
import string
import subprocess
import time
import traceback
import threading
import cherrypy
import jinja2
from src.URLHandler import URLHandler
from src.Streamer import Streamer
from pathlib import Path
import sys
import netifaces as ni
from cherrypy.process import plugins
import cv2

def testCamera(camId):
    cap = cv2.VideoCapture(camId)
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if w == 0 or h == 0:
        return -1
    ratio = w/h
    if ratio < 3:
        return camId
    if ratio > 3:
        return 100
    cap.release()

def selfTest():
    ret0 = testCamera(0)
    ret1 = testCamera(1)
    csi = -1
    zed = -1
    if ret0 == 0:
        csi = 0
    elif ret1 == 1:
        csi = 1
    if ret0 == 100:
        zed = 0
    elif ret1 == 100:
        zed = 1
    return csi, zed

class Server(object):
    def run(self, host="127.0.0.1", port=8000, dir='.', csiDevice=-1, zedDevice=-1):
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
                }
        }

        cherrypy.config.update({
            'server.socket_host': host,
            'server.socket_port': port,
        })
        if csiDevice == -1 or zedDevice == -1:
            csiDevice, zedDevice = selfTest()

        frameLock = threading.Lock()
        streamer = Streamer(frameLock, csiDevice)
        streamThread = threading.Thread(None, streamer.run, daemon=True)
        streamThread.start()

        cherrypy.quickstart(URLHandler(dir, streamer, frameLock, csiDevice, zedDevice, 300), '/', config=CP_CONF)

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

if __name__=="__main__": 
    main() 