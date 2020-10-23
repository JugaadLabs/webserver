ZED_ENABLED = True
try:
    import pyzed.sl as sl
except ImportError as e:
    ZED_ENABLED = False

params = {}

params["csiStreamer"] = {}
params["csiStreamer"]["resolution"] = (2592, 1944)
params["csiStreamer"]["recordingResolution"] = (540, 720)
params["csiStreamer"]["framerate"] = 30
params["csiStreamer"]["recordingInterval"] = 300

if ZED_ENABLED:
    params["zedStreamer"] = {}
    params["zedStreamer"]["resolution"] = sl.RESOLUTION.HD720
    params["zedStreamer"]["depth"] = sl.DEPTH_MODE.PERFORMANCE
    params["zedStreamer"]["framerate"] = 15
    params["zedStreamer"]["recordingInterval"] = 300

params["barcodeHandler"] = {}
# hmin,hmax,wmin,wmax, will be overriden if the crop is larger than the frame
params["barcodeHandler"]["crop"] = (0, 1000, 0, 1000)
params["barcodeHandler"]["previewResolution"] = (480, 427)
params["barcodeHandler"]["recordingResolution"] = (960, 854)
params["barcodeHandler"]["timeout"] = 500

params["recordingHandler"] = {}
params["recordingHandler"]["previewResolution"] = (480, 640)
params["recordingHandler"]["zedPreviewResolution"] = (360, 640)
