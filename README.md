## Introduction

This utility allows one to remotely record timestamped video data from a V4L2 camera and the ZED stereo camera simultaneously. It targets the NVIDIA Jetson Xavier, but should work fine with any computer with an NVIDIA graphics card which supports the ZED camera. If you don't have the ZED camera attached or `pysdk` installed, the server falls back to serving a video stream from a V4L2 device.

A video tutorial of using the dashboard can be found [here](https://youtu.be/_Sp9WvgxLE0).

## Install

Download the project using:

```
git clone https://github.com/JugaadLabs/webserver.git
```

Install the Python dependencies by running:

```
pip3 install -r requirements.txt
```

Install the ZED Python SDK using the instructions [here](https://www.stereolabs.com/docs/app-development/python/install/).

**Optional**: Autogenerate the `documentation.html` page by running:

```
pandoc README.md -o templates/documentation.html
```

## Usage

This project uses a CherryPy webserver for remotely receiving commands using HTTP GET calls. Make sure your Xavier NX is running Jetpack 4.4 Developer Preview for use with the e-Con camera. The e-Con camera is a V4L2 device and you can find which device it is by checking the output of `v4l2-ctl --list-devices`.

### Server

On the NVIDIA Jetson, the server can be started directly by using:

```
./startJetsonServer.sh
```

Start the webserver by running:

```
python3 webserver.py <INTERFACE='lo'> <PORT=8000> <RECORDING_DIR='.'> <V4L2_DEVICE=-1>
```

The `interface` argument is the network interface on which you want to run the webserver. Examples include `wlan0`, `lo`, and `l4tbr0` on the NVIDIA Jetson. The web server serves the page based on the IP address of the interface. The `RECORDING_DIR` argument is for choosing the folder to save the videos and images recorded by the cameras. The folder will be created if it doesn't already exist. The AR0591 camera module or any V4L2 webcam is auto-detected by default, but can also be specified in an argument. An example launch command where the camera is connected on `/dev/video1` is:

```
python3 webserver.py wlan0 8000 /home/nvidia/recordings 1
```

#### GUI Mode

Go to the address where the webserver is serving pages (e.g. http://192.168.55.1:8000) in your web browser. This loads a webpage with the options to control the cameras, take pictures for calibration, download files, and view documentation.

On recording a video, the videos will record to the specified location in the arguments. Each recording over 5 minutes is split into multiple files each 5 minutes long. Images captured for calibration are saved to `RECORDING_DIR/calibration`. Every file is timestamped.

### Recordings

The data from the ZED camera is saved in the SVO format. Instructions for processing this data can be found [here](https://www.stereolabs.com/docs/video/recording/).

Video from the V4L2 camera is saved to a timestamped `.avi` file. The UNIX timestamp for each frame of the video can be found in its accompanying `.pkl` file which contains a list of timestamps, one for each frame of the video. Please refer to the `dataprocess/dataprocess.ipynb` Jupyter notebook for processing the `.avi`, `.pkl`, `.svo` files.
