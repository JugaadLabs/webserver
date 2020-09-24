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
    def start(self):
        return "Started Recording!"

    @cherrypy.expose
    def pause(self):
        return "Paused Recording!"

    @cherrypy.expose
    def stop(self):
        return "Stopped Recording!"
