from typing import List
from tasks.project.packages.adjacent_lanes import AdjacentLane
from tasks.project.packages.ObjectDetector import Detection
from tasks.project.packages._aux import debug_print
from tasks.project.packages.settings import debugging

def isEmptyLaneNorth(detected_objects: List[Detection]) -> bool:
    for detected_object in detected_objects:
        bbox, score, cls_id = detected_object
        xmin, ymin, xmax, ymax = bbox
        xmid = (xmax + xmin)/2

        area = (xmax-xmin)*(ymax-ymin)
        debug_print(f"Detection on the left: cls_id={cls_id}, xmid={xmid}, area={area}", debugging)

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

        area = (xmax-xmin)*(ymax-ymin)
        debug_print(f"Detection on the right: cls_id={cls_id}, xmid={xmid}, area={area}", debugging)

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