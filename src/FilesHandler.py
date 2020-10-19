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

class FilesHandler:
    def __init__(self, recording_dir):
        self.template = Templates()
        self.recording_dir = recording_dir

    @cherrypy.expose
    def index(self, dir=None):
        if dir is None:
            dir = self.recording_dir
        dirs = []
        files = []
        for filename in glob.glob(dir + '/*'):
            absPath = os.path.abspath(filename)
            item = {}
            item['filename'] = os.path.basename(filename)
            item['path'] = absPath
            if os.path.isdir(absPath):
                dirs.append(item)
            else:
                files.append(item)
        dirs = sorted(dirs, key=itemgetter('filename'))
        files = sorted(files, key=itemgetter('filename'))
        return self.template.ls(files, dirs)
