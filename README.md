# luxonis-oak-object-tracker
A modified version of the example script for object tracking from luxonis

Updated from https://github.com/luxonis/depthai-python/tree/main/examples/ObjectTracker/object_tracker.py
by Jacob Harlow 
on 7-17-25

Set confidence threshold to 0.7
Set detection label to "bird"
Added Laplacian focus check using a threshold of 2000 
Set interval to 10s
Differentiated preview frame from high res video frame to ensure inference is done on 300x300 while saved frame is at 1080p
