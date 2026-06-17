from typing import List
from tasks.project.packages.adjacent_lanes import AdjacentLane
from tasks.project.packages.ObjectDetector import ObjectDetector, Detection

def decide_outgoing_lane(detected_objects: List[Detection]) -> AdjacentLane:
    duck_counter = 0

    if detected_objects is None:
        return AdjacentLane.west

    for detected_object in detected_objects:
        bbox, score, cls_id = detected_object

        if cls_id == 0:
            duck_counter += 1

            duck_bbox = bbox

    if duck_counter == 0:
        return AdjacentLane.west
    
    elif duck_counter == 1:
        xmin, ymin, xmax, ymax = duck_bbox
        xmid = (xmax + xmin)/2

        if xmid < 320:
            return AdjacentLane.north
        else:
            return AdjacentLane.east
    
    else:
        raise ValueError("Too many ducks!")
    
def recheck_outgoing_lane(detected_objects: List[Detection], current_assumption: AdjacentLane) -> AdjacentLane:
    new_assumption = decide_outgoing_lane(detected_objects)

    if current_assumption == AdjacentLane.west:
        return new_assumption
    
    elif new_assumption == AdjacentLane.west:
        return current_assumption
    
    elif current_assumption == new_assumption:
        return current_assumption
    
    else:
        raise ValueError("Too many ducks or ducks have been moved!")