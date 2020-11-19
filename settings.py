ZED_ENABLED = True
try:
    import pyzed.sl as sl
except ImportError as e:
    ZED_ENABLED = False

params = {}

params["csiStreamer"] = {}
params["csiStreamer"]["hdResolution"] = (2592, 1944)
params["csiStreamer"]["stdResolution"] = (640, 480)
params["csiStreamer"]["recordingResolution"] = (540, 720)
params["csiStreamer"]["framerate"] = 20
params["csiStreamer"]["recordingInterval"] = 300

if ZED_ENABLED:
    params["zedStreamer"] = {}
    params["zedStreamer"]["resolution"] = sl.RESOLUTION.HD720
    params["zedStreamer"]["depth"] = sl.DEPTH_MODE.PERFORMANCE
    params["zedStreamer"]["framerate"] = 15
    params["zedStreamer"]["recordingInterval"] = 300

params["barcodeHandler"] = {}
# hmin,hmax,wmin,wmax, will be overriden if the crop is larger than the frame
params["barcodeHandler"]["crop"] = (972, 1620, 0, 1944)
params["barcodeHandler"]["previewResolution"] = (960, 320)
params["barcodeHandler"]["recordingResolution"] = (1944, 480)
params["barcodeHandler"]["timeout"] = 500

params["recordingHandler"] = {}
params["recordingHandler"]["previewResolution"] = (480, 640)
params["recordingHandler"]["zedPreviewResolution"] = (360, 640)

params["detectionHandler"] = {}
params["detectionHandler"]["framerate"] = 9
params["detectionHandler"]["recordingResolution"] = (480, 640)
params["detectionHandler"]["enginepath"] = "/home/nvidia/webserver/src/uilts/forklift_68fds_3cls_1.trt"
params["detectionHandler"]["H"] = 2.0758491535847865
params["detectionHandler"]["L0"] = 0.3106217478768165
