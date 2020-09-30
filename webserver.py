import os
import sys
import string
import subprocess
import time
import traceback
import threading
import cherrypy
import jinja2
from URLHandler import URLHandler
import sys
import netifaces as ni

class Server(object):
    def run(self, host="127.0.0.1", port=8000):
        cherrypy.tree.mount(URLHandler(self), '/', None)
        cherrypy.config.update({
            'server.socket_host': host,
            'server.socket_port': port
        })
        cherrypy.engine.start()
        cherrypy.engine.block()

def main():
    server = Server()
    if len(sys.argv) >= 2:
        server.run(sys.argv[1])
    else:
        ip = ni.ifaddresses('lo')[ni.AF_INET][0]['addr']
        server.run(ip)

if __name__=="__main__": 
    main() 