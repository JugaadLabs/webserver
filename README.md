## Introduction

This utility allows one to remotely record timestamped video data from a V4L2 camera and the ZED stereo camera simultaneously. It targets the NVIDIA Jetson Xavier, but should work fine with any computer with an NVIDIA graphics card which supports the ZED camera.

## Install

Download the project using:

```
git clone https://github.com/JugaadLabs/webserver.git
```

Install the Python dependencies by running:

```
pip install -r requirements.txt
```

Install the ZED Python SDK using the instructions [here](https://www.stereolabs.com/docs/app-development/python/install/).

**Optional**: Autogenerate the `documentation.html` page by running:

```
pandoc README.md -o html/documentation.html
```

## Usage

This project uses a CherryPy webserver for remotely receiving commands using HTTP GET calls. Make sure your Xavier NX is running Jetpack 4.4 Developer Preview for use with the e-Con camera. The e-Con camera is a V4L2 device and you can find which device it is by checking the out of `v4l2-ctl --list-devices`.

### Server

Start the webserver by running:

```
python3 webserver.py <INTERFACE='lo'> <PORT=8000> <RECORDING_DIR='.'> <V4L DEVICE>
```

The `interface` argument is the network interface on which you want to run the webserver. Examples include `wlan0`, `lo`, and `l4tbr0` on Jetsons. The web server serves the page based on the IP address of the interface. The `recording_dir` argument is for choosing the folder to save the videos recorded by the cameras. V4L device is the `X` in `/dev/videoX` for the camera from which you want to record video from. Use `v4l-utils` to figure out what the device ID of the CSI camera is. For example, the following command uses port 9999 on the IP address the Xavier is connected to on its wireless interface and streams video from `/dev/video1`:

```
python3 webserver.py wlan0 9999 /home/nvidia/myrecordings 1
```

### Client

#### CLI Mode

In CLI mode, the webserver can execute commands sent using the `client.py` program:

```
python3 client.py --<record|stop|pause> <all|csi|zed> <--host IP --port PORT>
```

For example, to record video from both the cameras we can run:

```
python3 client.py --record all --host 192.168.55.1 --port 8000
```

#### GUI Mode

Go to the address where the webserver is serving pages (e.g. http://192.168.55.1:8000) in your web browser. This loads a webpage with the options to control the cameras, download files, and view documentation.

### Recordings

The data from the ZED camera is saved in the SVO format. Instructions for processing this data can be found [here](https://www.stereolabs.com/docs/video/recording/). 

Video from the V4L2 camera is saved to a timestamped `.avi` file. The UNIX timestamp for each frame of the video can be found in its accompanying `.pkl` file which contains a list of timestamps, one for each frame of the video.