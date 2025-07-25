#!/usr/bin/env python3

"""
Updated from https://github.com/luxonis/depthai-python/tree/main/examples/ObjectTracker/object_tracker.py
by Jacob Harlow 
on 7-17-25

Set confidence threshold to 0.7
Set detection label to "bird"
Added Laplacian focus check using a threshold of 2000 
Set interval to 10s
Differentiated preview frame from high res video frame to ensure inference is done on 300x300 while saved frame is at 1080p

Updated on 7-19-25
Set tracker type to ZERO_TERM_IMAGELESS
Now collects a 5 frame set upon detection and saves the sharpest
"""

from pathlib import Path
import cv2
import depthai as dai
import numpy as np
import time
import argparse

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
            "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

nnPathDefault = str((Path(__file__).parent / Path('../models/mobilenet-ssd_openvino_2021.4_6shave.blob')).resolve().absolute())
parser = argparse.ArgumentParser()
parser.add_argument('nnPath', nargs='?', help="Path to mobilenet detection network blob", default=nnPathDefault)
parser.add_argument('-ff', '--full_frame', action="store_true", help="Perform tracking on full RGB frame", default=False)

args = parser.parse_args()

fullFrameTracking = args.full_frame

# Create pipeline
pipeline = dai.Pipeline()

# Define nodes
camRgb = pipeline.create(dai.node.ColorCamera)
detectionNetwork = pipeline.create(dai.node.MobileNetDetectionNetwork)
objectTracker = pipeline.create(dai.node.ObjectTracker)

xlinkOut = pipeline.create(dai.node.XLinkOut)
trackerOut = pipeline.create(dai.node.XLinkOut)
videoOut = pipeline.create(dai.node.XLinkOut)
# controlIn = pipeline.create(dai.node.XLinkIn)

xlinkOut.setStreamName("preview")
trackerOut.setStreamName("tracklets")
videoOut.setStreamName("video")

# Configure camera
camRgb.setPreviewSize(300, 300)
camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
camRgb.setInterleaved(False)
camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
camRgb.setFps(40)

# Link outputs
camRgb.preview.link(detectionNetwork.input)
camRgb.video.link(videoOut.input)
objectTracker.passthroughTrackerFrame.link(xlinkOut.input)

# Neural Network
detectionNetwork.setBlobPath(args.nnPath)
detectionNetwork.setConfidenceThreshold(0.7)
detectionNetwork.input.setBlocking(False)

objectTracker.setDetectionLabelsToTrack([3])  # only track "bird"
# possible tracking types: ZERO_TERM_COLOR_HISTOGRAM, ZERO_TERM_IMAGELESS, SHORT_TERM_IMAGELESS, SHORT_TERM_KCF
objectTracker.setTrackerType(dai.TrackerType.ZERO_TERM_IMAGELESS)
# take the smallest ID when new object is tracked, possible options: SMALLEST_ID, UNIQUE_ID
objectTracker.setTrackerIdAssignmentPolicy(dai.TrackerIdAssignmentPolicy.SMALLEST_ID)

if fullFrameTracking:
    camRgb.video.link(objectTracker.inputTrackerFrame)
else:
    detectionNetwork.passthrough.link(objectTracker.inputTrackerFrame)

detectionNetwork.passthrough.link(objectTracker.inputDetectionFrame)
detectionNetwork.out.link(objectTracker.inputDetections)
objectTracker.out.link(trackerOut.input)

# Focus check using Laplacian
def is_image_in_focus(image, threshold=100.0):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return lap_var > threshold, lap_var

# Connect to device and start pipeline
with dai.Device(pipeline) as device:
    videoQueue = device.getOutputQueue("video", 4, False)
    preview = device.getOutputQueue("preview", 4, False)
    tracklets = device.getOutputQueue("tracklets", 4, False)

    startTime = time.monotonic()
    counter = 0
    fps = 0
    last_saved_time = 0  # Track last bird frame capture

    while True:
        imgFrame = preview.get()
        videoFrame = videoQueue.get()
        track = tracklets.get()

        previewFrame = imgFrame.getCvFrame() # Inference and Preview frame 300x300
        highResFrame = videoFrame.getCvFrame()  # High-res frame to display/save

        counter += 1
        current_time = time.monotonic()
        if (current_time - startTime) > 1:
            fps = counter / (current_time - startTime)
            counter = 0
            startTime = current_time

        color = (255, 0, 0)
        trackletsData = track.tracklets
        bird_detected = False

        for t in trackletsData:
            roi = t.roi.denormalize(previewFrame.shape[1], previewFrame.shape[0])
            x1 = int(roi.topLeft().x)
            y1 = int(roi.topLeft().y)
            x2 = int(roi.bottomRight().x)
            y2 = int(roi.bottomRight().y)

            try:
                label = labelMap[t.label]
            except:
                label = str(t.label)

            # Draw detections
            cv2.putText(previewFrame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(previewFrame, f"ID: {[t.id]}", (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(previewFrame, t.status.name, (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.rectangle(previewFrame, (x1, y1), (x2, y2), color, cv2.FONT_HERSHEY_SIMPLEX)

            # Bird detection
            if label.lower() == "bird":
                bird_detected = True

        # Save high res frame if bird found, in focus and 10s passed
        if bird_detected and (time.monotonic() - last_saved_time) > 10:
            print("[INFO] Bird detected. Capturing up to 5 valid frames for focus check...")
            frame_batch = []

            attempts = 0
            while len(frame_batch) < 5 and attempts < 10:
                preview_frame = preview.get().getCvFrame()
                video_frame = videoQueue.get().getCvFrame()
                track = tracklets.get()
                trackletsData = track.tracklets

                found_bird = any(labelMap[t.label].lower() == "bird" for t in trackletsData)
                if found_bird:
                    frame_batch.append(video_frame)
                    # print(f"[INFO] Valid bird frame collected ({len(frame_batch)}/5)")
                # else:
                    # print("[INFO] Frame skipped: no bird detected.")

                attempts += 1
                time.sleep(0.2)

            if not frame_batch:
                print("[SKIPPED] No valid bird frames collected in batch.")
                continue

            # Select the sharpest frame from valid ones
            best_frame = None
            best_sharpness = 0

            for i, frame in enumerate(frame_batch):
                _, sharpness = is_image_in_focus(frame)
                # print(f"[DEBUG] Frame {i+1} sharpness: {sharpness:.1f}")
                if sharpness > best_sharpness:
                    best_sharpness = sharpness
                    best_frame = frame

            if best_sharpness > 2000.0:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"bird_detected_{timestamp}.png"
                cv2.imwrite(filename, best_frame)
                print(f"[INFO] Saved sharpest frame (sharpness={best_sharpness:.1f}) as {filename}")
                last_saved_time = time.monotonic()
            else:
                print(f"[SKIPPED] No sharp frame found (best={best_sharpness:.1f})")

        # Show preview display
        cv2.imshow("tracker", previewFrame)

        if cv2.waitKey(1) == ord('q'):
            break

