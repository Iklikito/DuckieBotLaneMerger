import numpy as np
from typing import List
import cv2
from tasks.project.packages.adjacent_lanes import AdjacentLane
from tasks.project.packages.ObjectDetector import Detection
#from adjacent_lanes import AdjacentLane
#from ObjectDetector import ObjectDetector, Detection

def isEmptyLaneNorth(detected_objects: List[Detection]) -> bool:
    for detected_object in detected_objects:
        bbox, score, cls_id = detected_object
        xmin, ymin, xmax, ymax = bbox
        xmid = (xmax + xmin)/2

        if cls_id == 1 and xmid < 320:
            print("North lane is not empty")
            return False
        
    print("North lane is empty")
    return True
    
def isEmptyLaneEast(detected_objects: List[Detection]) -> bool:
    for detected_object in detected_objects:
        bbox, score, cls_id = detected_object
        xmin, ymin, xmax, ymax = bbox
        xmid = (xmax + xmin)/2

        print(f"Detection: cls_id={cls_id}, xmid={xmid}")

        if cls_id == 1 and xmid >= 320:
            print("East lane is not empty")
            return False
        
    print("East lane is empty")
    return True

def areEmptyLanesUntil(outgoing_lane: AdjacentLane, detected_objects: List[Detection]) -> bool:
    
    if detected_objects is None:
        return False
    
    if outgoing_lane == AdjacentLane.east:
        return True
    
    elif outgoing_lane == AdjacentLane.north:
        return isEmptyLaneEast(detected_objects)
    
    elif outgoing_lane == AdjacentLane.west:
        return isEmptyLaneEast(detected_objects) and isEmptyLaneNorth(detected_objects)
    
    else:
        raise ValueError("Invalid outgoing lane for areEmptyLanesUntil")