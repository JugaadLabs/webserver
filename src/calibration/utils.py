import numpy as np
np.set_printoptions(formatter={'float': lambda x: "{0:0.4f}".format(x)})

import cv2
import glob
import matplotlib.pyplot as plt
import json



def get_pose(images,objp,chessboard_size,camera_intrinsic_path,rotate_flag):

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1)
    objpoints = [] 
    imgpoints = [] 
    for fname in images:
        img = cv2.imread(fname)
        if rotate_flag:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

        ret, corners = cv2.findChessboardCorners(gray, chessboard_size,None)
        
        if ret == True:
            objpoints.append(objp)

            corners2 = cv2.cornerSubPix(gray,corners,(3,3),(-1,-1),criteria)
            temp = corners2.copy()
            imgpoints.append(temp)
            # print(imgpoints[-1][0])
            
            # uncomment to check the detection if needed
            # img = cv2.drawChessboardCorners(img, chessboard_size, corners2,ret)
            # plt.imshow(img)
            # plt.show()

    with open(camera_intrinsic_path) as f:
        intrinsics = json.load(f)

    mtx = np.array(intrinsics['K'])
    dist = np.array(intrinsics['distortion'])

    pose_mats = []
    for i in range(len(images)):
        ret, rvec, tvec = cv2.solvePnP(objpoints[i], imgpoints[i], mtx, dist)
        rotation_mat, _ = cv2.Rodrigues(rvec)
        pose_mat = cv2.hconcat((rotation_mat, tvec))
        pose_mat = np.vstack((pose_mat,np.array([0,0,0,1]).reshape(1,-1)))
        pose_mats.append(pose_mat)
    
    return pose_mat
    

def register_depth(cam_image,point_cloud,monocam_intrinsics_path,extrinsics_path):
    cam_image = cv2.rotate(cam_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    with open(extrinsics_path) as f:
        extrinsics = json.load(f)
    with open(monocam_intrinsics_path) as f:
        monocam_intrinsics = json.load(f)

    cam_K = np.array(monocam_intrinsics['K'])
    Transformation = np.array(extrinsics['Transformation'])
    point_cloud_homo = point_cloud.copy()
    point_cloud_homo[:,3] = 1
    point_cloud_homo[0],np.sum(point_cloud_homo[0][:-1]**2)**0.5

    transformed_pc_coords = (Transformation.dot(point_cloud_homo.T)).T
    transformed_pc_coords = transformed_pc_coords[:,:-1]
    transformed_pc_dists = np.sum(transformed_pc_coords**2,axis=1)**0.5

    uv_pc_coords = cam_K.dot((transformed_pc_coords/transformed_pc_coords[:,-1].reshape(-1,1)).T)
    uv_pc_coords.shape,np.max(uv_pc_coords,axis=1),np.min(uv_pc_coords,axis=1)

    uv_pc_coords[2] = transformed_pc_dists 
    uv_pc_coords_filter_mask = (uv_pc_coords[0]>0)*(uv_pc_coords[0]<cam_image.shape[1]-1)*(uv_pc_coords[1]>0)*(uv_pc_coords[1]<cam_image.shape[0]-1)
    uv_pc_coords_filtered = uv_pc_coords[:,uv_pc_coords_filter_mask]
    uv_pc_coords_filtered_processed = np.rint(uv_pc_coords_filtered)
    uv_pc_coords_filtered_processed = uv_pc_coords_filtered_processed.astype(int)
    depth = np.zeros(cam_image.shape[:-1])
    depth[uv_pc_coords_filtered_processed[1],uv_pc_coords_filtered_processed[0]]=uv_pc_coords_filtered_processed[2]
    # plt.imshow(depth)
    # plt.show()
    return depth,cam_image