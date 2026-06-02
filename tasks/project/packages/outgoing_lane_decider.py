import numpy as np
from tasks.project.packages.adjacent_lanes import AdjacentLane
from tasks.project.packages.ObjectDetector import ObjectDetector

def decide_outgoing_lane(frame: np.ndarray, object_detector: ObjectDetector) -> AdjacentLane:
    detected_objects = object_detector.detect(frame)
    duck_counter = 0

    if detected_objects is None:
        return AdjacentLane.east

    for detected_object in detected_objects:
        bbox, score, cls_id = detected_object

        if cls_id == 0:
            duck_counter += 1

    if duck_counter == 0:
        return AdjacentLane.west
    
    elif duck_counter == 1:
        xmin, ymin, xmax, ymax = bbox
        xmid = (xmax + xmin)/2

        if xmid < 320:
            return AdjacentLane.north
        else:
            return AdjacentLane.east
    
    else:
        raise ValueError("Too many ducks")