#%%
from utils import *

# INPUTS

# [ALL THE DATA REQUIRED FOR ZED IS FOR THE LEFT CAMERA]

chessboard_size = (6,9) # Provide chessboard size [rows,columns]
square_size = 25.4 # Provide the size of each square in 'mm'
path_to_monocam_image = 'econ2/ext1/*.jpg' # path to monocam image and extension
path_to_zed_image = 'zed_images/ext1/*.png' # path to zed image and extension
monocam_intrinsic_path = 'econ2/intrinsics.json' # path to monocam intrinsic
zed_intrinsic_path = 'zed_images/intrinsics.json' # path to zed intrinsic
path_to_save_extrinsics = 'extrinsics.json' 


# EXTRINSICS CALCULATION
objp = np.zeros((chessboard_size[0]*chessboard_size[1],3), np.float32)
objp[:,:2] = np.mgrid[0:chessboard_size[0],0:chessboard_size[1]].T.reshape(-1,2)
objp = objp*square_size

mono_cam_images = glob.glob(path_to_monocam_image) #images directory and extension
zed_images = glob.glob(path_to_zed_image) #images directory and extension



P1 = get_pose(mono_cam_images,objp,chessboard_size,monocam_intrinsic_path,1)
P2 = get_pose(zed_images,objp,chessboard_size,zed_intrinsic_path,0)

Transformation = P1.dot(np.linalg.inv(P2))


# dump to json file
extrinsics = {'Transformation':Transformation.tolist()}
with open(path_to_save_extrinsics, 'w') as fp:
    json.dump(extrinsics, fp)
