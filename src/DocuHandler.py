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
import simplejson
from pathlib import Path
from operator import itemgetter

from src.templates import Templates

class DocuHandler:
    def __init__(self):
        self.template = Templates()

    @cherrypy.expose
    def index(self):
        return self.template.documentation()
