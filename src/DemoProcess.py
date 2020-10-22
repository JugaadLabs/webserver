import numpy as np
from src.zmq_utils import zmqNode
import time
from tqdm import tqdm

def main():
    inputResolution = (480, 640)

    sendImgNode = zmqNode('send', 9500)
    recvResultsNode = zmqNode('recv', 9501)

    for i in tqdm(range(10000)):
        img = np.random.rand(480,640,3)
        sendImgNode.send_array(img)
        dataDict = recvResultsNode.recv_zipped_pickle()
        print(dataDict['birdsView'].shape)

if __name__ == "__main__":
    main()
