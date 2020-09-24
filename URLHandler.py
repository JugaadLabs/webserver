import os
import sys
import string
import subprocess
import time
import traceback
import threading
import cherrypy
import jinja2

class URLHandler(object):
    def __init__(self, config):
        self.config = config

    @cherrypy.expose
    def record(self, device=None):
        if device == 'csi':
            print(device)
        elif device == 'zed':
            print(device)
        elif device == 'all':
            print(device)
        return "OK"

    @cherrypy.expose
    def pause(self, device=None):
        if device == 'csi':
            print(device)
        elif device == 'zed':
            print(device)
        elif device == 'all':
            print(device)
        return "OK"

    @cherrypy.expose
    def stop(self, device=None):
        if device == 'csi':
            print(device)
        elif device == 'zed':
            print(device)
        elif device == 'all':
            print(device)
        return "OK"
