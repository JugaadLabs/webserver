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
from PIL import Image
import simplejson
from pathlib import Path
from operator import itemgetter

class BarcodeHandler(object):
    def __init__(self):
        print("Barcode ready lah!")

    @cherrypy.expose
    def index(self):
        return "Hello bob"