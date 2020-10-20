from imutils.video import VideoStream
from pyzbar import pyzbar
import argparse
import datetime
import imutils
import time
import cv2
from pylibdmtx import pylibdmtx
import numpy as np


class BarcodeScanner:

    def __init__(self, timeout):
        self.timeout = timeout  # timeout for barcode reader

    def readImage(self, image):
        self.image = image
        self.img_h, self.img_w, _ = image.shape

    def grayscaleStats(self):
        self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        # calculate average brighness
        self.gray_mean = np.mean(self.gray)
        # correct image brightness and contrast
        self.correctted_mean = self.gray_mean

        if(self.gray_mean < 130):
            self.image = cv2.convertScaleAbs(self.image, alpha=1.0, beta=20)
            self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
            self.correctted_mean = np.mean(self.gray)

        self.gray_max = np.max(self.gray)
        self.gray_min = np.min(self.gray)
        self.contrast_ratio = (self.gray_max - self.gray_min) / \
            (np.uint16(self.gray_max) + np.uint16(self.gray_min))
        # print("gray max:",self.gray_max,"gray min:",self.gray_min,"contrast ratio:",self.contrast_ratio)
        text = "brighness:{:.0f} ,contrast ratio:{:.0f}%, corrected brighness:{:.0f}".format(
            self.gray_mean, self.contrast_ratio*100, self.correctted_mean)
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(self.image, text, (0, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    def decodeBarcodes(self):
        self.bcs = pyzbar.decode(self.image)  # barcodes
        self.dms = pylibdmtx.decode(
            self.image, timeout=self.timeout)  # datamatrices

        self.bcs_list = []
        self.dms_list = []

        for barcode in self.bcs:
            barcodeData = barcode.data.decode("utf-8")
            barcodeType = barcode.type
            self.bcs_list.append([barcodeData, barcodeType])

        for dm in self.dms:
            dmData = dm.data.decode("utf-8")
            self.dms_list.append(dmData)

    def drawBbox(self):
        for barcode in self.bcs:
            # extract the bounding box location of the barcode and draw
            # the bounding box surrounding the barcode on the image
            (x, y, w, h) = barcode.rect
            cv2.rectangle(self.image, (x, y), (x + w, y + h), (0, 0, 255), 2)
            barcodeData = barcode.data.decode("utf-8")
            barcodeType = barcode.type
            text = "{} ({})".format(barcodeData, barcodeType)
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(self.image, text, (x, y - 10),
                        font, 0.5, (0, 0, 255), 2)

        for dm in self.dms:
            (x, y, w, h) = dm.rect
            y = self.img_h - y
            cv2.rectangle(self.image, (x, y), (x + w, y - h), (0, 0, 255), 2)
            dmData = dm.data.decode("utf-8")
            text = "{}".format(dmData)
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(self.image, text, (x, y - h - 10),
                        font, 0.5, (0, 0, 255), 2)


if __name__ == "__main__":

    vs = VideoStream(src=2).start()
    time.sleep(1.0)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    # out = cv2.VideoWriter('output.avi',fourcc, 10.0, (1920,1080))
    out = cv2.VideoWriter('output.avi', fourcc, 10.0, (640, 480))

    myScanner = BarcodeScanner(timeout=50)

    while True:
        image = vs.read()
        myScanner.readImage(image)
        myScanner.grayscaleStats()
        myScanner.decodeBarcodes()
        print(myScanner.dms_list)
        myScanner.drawBbox()

        out.write(myScanner.image)
        print("resolution:", myScanner.img_w, myScanner.img_h)
        # show the output frame
        cv2.namedWindow("Barcode Scanner", cv2.WINDOW_NORMAL)
        # cv2.resizeWindow("Barcode Scanner", 800,800)
        cv2.imshow("Barcode Scanner", myScanner.image)
        key = cv2.waitKey(1) & 0xFF
        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
            break

    cv2.destroyAllWindows()
    out.release()
    vs.stop()
