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
import threading
import enum
import glob
import cv2
import datetime
from PIL import Image
import simplejson
from pathlib import Path
from operator import itemgetter

from src.templates import Templates

class DisabledHandler(object):
    def __init__(self):
        cherrypy.log("Activating disabled page handler")
        self.template = Templates()

    @cherrypy.expose
    def index(self):
        return self.template.disabled()

