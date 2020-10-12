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
from pathlib import Path
import sys
import netifaces as ni
from cherrypy.process import plugins

class Server(object):
    def run(self, host="127.0.0.1", port=8000, dir='.', csiDevice=0):
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
        cherrypy.quickstart(URLHandler(self, dir, csiDevice, 300), '/', config=CP_CONF)

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