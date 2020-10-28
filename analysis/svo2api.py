import numpy as np
from scipy import interpolate
import os
import PIL.Image as Image
import cv2
import pickle as pkl
import pyzed.sl as sl
import bisect
from matplotlib import pyplot as plt
from tqdm import tqdm


DIR = '/home/nvidia/recordings/'
ZED_SVO = 'ZED_2020-10-28-19-25-22.svo'
ZED_SVO_PATH = os.path.join(DIR, ZED_SVO)

framerate = 20
resolution = (1280, 720)

fourcc = cv2.VideoWriter_fourcc(*'XVID')
colorVideoOut = cv2.VideoWriter('color.avi', fourcc, framerate, resolution)
depthVideoOut = cv2.VideoWriter('depth.avi', fourcc, framerate, resolution)

init_parameters = sl.InitParameters()
init_parameters.set_from_svo_file(ZED_SVO_PATH)

zed = sl.Camera()
err = zed.open(init_parameters)
runtime = sl.RuntimeParameters()
svo_image = sl.Mat(resolution[1], resolution[0], sl.MAT_TYPE.U8_C4)
depth_map = sl.Mat(resolution[1], resolution[0], sl.MAT_TYPE.U8_C4)
i = 0
for i in tqdm(range(zed.get_svo_number_of_frames())):
    if zed.grab(runtime) == sl.ERROR_CODE.SUCCESS:
        i+=1
        zed.retrieve_image(svo_image, sl.VIEW.LEFT, sl.MEM.CPU)
        zed.retrieve_image(depth_map, sl.VIEW.DEPTH, sl.MEM.CPU)
        colorNumpy = svo_image.get_data()
        colorNumpy = cv2.resize(colorNumpy, resolution, cv2.INTER_AREA)
        colorNumpy = cv2.cvtColor(colorNumpy, cv2.COLOR_RGBA2RGB)
        colorVideoOut.write(colorNumpy)

        depthNumpy = depth_map.get_data()
        depthNumpy = cv2.resize(depthNumpy, resolution, cv2.INTER_AREA)
        depthNumpy = cv2.cvtColor(depthNumpy, cv2.COLOR_BGR2RGB)
        depthVideoOut.write(depthNumpy)
        t = zed.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_nanoseconds()/1e9
    else:
        break
depthVideoOut.release()
colorVideoOut.release()
print("Videos saved")