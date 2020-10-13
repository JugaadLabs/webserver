import numpy as np
import cv2
import glob
import matplotlib.pylab as plt
import json


# INPUTS
chessboard_size = (6,9) # Provide chessboard size [rows,columns]
square_size = 25.4 # Provide the size of each square in 'mm'
path_to_images = 'econ2/calibration/*.jpg' # path to images and extension
path_to_save_intrinsics = 'econ2/intrinsics22.json'

# CALIBRATION
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1)
objp = np.zeros((chessboard_size[0]*chessboard_size[1],3), np.float32)
objp[:,:2] = np.mgrid[0:chessboard_size[0],0:chessboard_size[1]].T.reshape(-1,2)
objp = objp*square_size

objpoints = [] 
imgpoints = [] 

images = glob.glob(path_to_images) 

for fname in images[::1]:
    img = cv2.imread(fname)

    # Rotate if the camera is placed rotated
    img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, chessboard_size,None)
    if ret == True:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray,corners,(3,3),(-1,-1),criteria)
        imgpoints.append(corners2)
        
        # uncomment to check the detection if needed
        # img = cv2.drawChessboardCorners(img, chessboard_size, corners2,ret)
        # plt.imshow(img)
        # plt.show()

ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1],None,None)

# dump to json file
intrinsics = {'K':mtx.tolist(),'distortion':dist.tolist()}
with open(path_to_save_intrinsics, 'w') as fp:
    json.dump(intrinsics, fp)
