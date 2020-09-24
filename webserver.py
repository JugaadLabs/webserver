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

class Server(object):
    def run(self, ip="127.0.0.1", port=8000):
        cherrypy.tree.mount(URLHandler(self), '/', None)
        cherrypy.config.update({
            'server.socket_host': ip,
            'server.socket_port': port
        })
        cherrypy.engine.start()
        cherrypy.engine.block()

def main(): 
    server = Server()
    server.run()

if __name__=="__main__": 
    main() 