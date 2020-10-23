import zmq
import numpy as np
import pickle
import zlib

class zmqNode():

    def __init__(self, mode, port):
        context = zmq.Context()
        if mode == 'send':
            self.socket = context.socket(zmq.PUB)
            self.socket.setsockopt(zmq.SNDHWM, 1)
            self.socket.bind("tcp://*:{:d}".format(port))
            print('Sending on {:d}'.format(port))
        elif mode == 'recv':
            self.socket = context.socket(zmq.SUB)
            self.socket.setsockopt(zmq.SUBSCRIBE, b"")
            self.socket.setsockopt(zmq.RCVHWM, 1)
            self.socket.connect("tcp://localhost:{:d}".format(port))
            self.socket.RCVTIMEO = 10
            print("Collecting on {:d}".format(port))

    def send_array(self, A, flags=0, copy=True, track=False):
        """send a numpy array with metadata"""
        md = dict(
            dtype = str(A.dtype),
            shape = A.shape,
        )
        self.socket.send_json(md, flags|zmq.SNDMORE)
        return self.socket.send(A, flags, copy=copy, track=track)

    def recv_array(self, flags=0, copy=True, track=False):
        """ZMQ recv a numpy array"""
        md = self.socket.recv_json(flags=flags) 
        msg = self.socket.recv(flags=flags, copy=copy, track=track)
        buf = bytes(memoryview(msg))
        A = np.frombuffer(buf, dtype=md['dtype'])
        return A.reshape(md['shape'])

    def send_zipped_pickle(self, obj, flags=0, protocol=-1):
        """pickle an object, and zip the pickle before sending it"""
        p = pickle.dumps(obj, protocol)
        z = p#zlib.compress(p)
        return self.socket.send(p, flags=flags)
    
    def recv_zipped_pickle(self, flags=0, protocol=-1):
        z = self.socket.recv(flags)
        p = z#zlib.decompress(z)
        return pickle.loads(p)