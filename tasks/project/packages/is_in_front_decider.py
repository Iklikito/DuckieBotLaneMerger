import cv2
import numpy as np

_UPPER_THRESHOLD_RED = 4600
_LOWER_THRESHOLD_RED = 200

_hsv_bounds = {
    'lo1': [0,   120, 100],
    'hi1': [10,  255, 255],
    'lo2': [170, 120, 100],
    'hi2': [180, 255, 255],
}

def get_hsv_bounds() -> dict:
    return {k: list(v) for k, v in _hsv_bounds.items()}

def set_hsv_bounds(lo1=None, hi1=None, lo2=None, hi2=None):
    if lo1 is not None: _hsv_bounds['lo1'] = list(lo1)
    if hi1 is not None: _hsv_bounds['hi1'] = list(hi1)
    if lo2 is not None: _hsv_bounds['lo2'] = list(lo2)
    if hi2 is not None: _hsv_bounds['hi2'] = list(hi2)

def get_red_mask(frame) -> np.ndarray:
    """Return a binary mask of red pixels in the entire frame."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array(_hsv_bounds['lo1']), np.array(_hsv_bounds['hi1']))
    mask2 = cv2.inRange(hsv, np.array(_hsv_bounds['lo2']), np.array(_hsv_bounds['hi2']))
    return mask1 | mask2

def is_in_front(frame) -> bool:
    mask = get_red_mask(frame)
    h = mask.shape[0]
    bottom_quarter = mask[int(h * 0.75):, :]
    print("Looking for red line...")
    if frame is None:
        print("Frame is none.")
    else:
        print(int(np.count_nonzero(bottom_quarter)) > _UPPER_THRESHOLD_RED) 
    print(f"NUmber of red pixels: {int(np.count_nonzero(bottom_quarter))}")   
    return int(np.count_nonzero(bottom_quarter)) > _UPPER_THRESHOLD_RED

def has_passed_red_line(frame) -> bool:
    print("Waiting for red line to disappear...")
    mask = get_red_mask(frame)
    h = mask.shape[0]
    bottom_quarter = mask[int(h * 0.75):, :]
    print("Looking for red line...")
    if frame is None:
        print("Frame is none.")
    else:
        print(int(np.count_nonzero(bottom_quarter)) < _LOWER_THRESHOLD_RED)    
    return int(np.count_nonzero(bottom_quarter)) < _LOWER_THRESHOLD_RED