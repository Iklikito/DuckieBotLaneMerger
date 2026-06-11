from typing import Tuple
import os
import numpy as np
import cv2
import yaml

_HSV_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'lane_servoing_hsv_config.yaml')
try:
    with open(_HSV_FILE) as _f:
        _h = yaml.safe_load(_f) or {}
except FileNotFoundError:
    _h = {}

_yellow_lower = np.array([_h.get('yellow_lower_h', 0),  _h.get('yellow_lower_s', 0),  _h.get('yellow_lower_v', 0)])
_yellow_upper = np.array([_h.get('yellow_upper_h', 0),  _h.get('yellow_upper_s', 0), _h.get('yellow_upper_v', 0)])

_white_lower = np.array([_h.get('white_lower_h', 0),   _h.get('white_lower_s', 0), _h.get('white_lower_v', 0)])
_white_upper = np.array([_h.get('white_upper_h', 0), _h.get('white_upper_s', 0), _h.get('white_upper_v', 0)])

def detect_lane_markings(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    h, w = image.shape[:2]

    # Noise reduction
    blurred = cv2.GaussianBlur(image, (5, 5), 0)

    # HSV conversion
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # Color masks
    mask_yellow = cv2.inRange(hsv, _yellow_lower, _yellow_upper)
    mask_white  = cv2.inRange(hsv, _white_lower,  _white_upper)

    # Ignore sky / upper image region
    mask_horizon = np.zeros((h, w), dtype=np.uint8)
    mask_horizon[int(h * 0.2):, :] = 255

    # Ignore far-left region for white lane
    mask_white_area = np.ones((h, w), dtype=np.uint8) * 255
    mask_white_area[:, : w//4] = 0

    # Apply region masks
    mask_yellow = cv2.bitwise_and(mask_yellow, mask_horizon)
    mask_white = cv2.bitwise_and(mask_white, mask_horizon)
    mask_white = cv2.bitwise_and(mask_white, mask_white_area)

    # Convert to 0/1 float masks if the rest of your pipeline expects floats
    mask_yellow = (mask_yellow > 0).astype(float)
    mask_white = (mask_white > 0).astype(float)

    return mask_yellow, mask_white




def set_hsv_bounds(yellow_lower, yellow_upper, white_lower, white_upper):
    global _yellow_lower, _yellow_upper, _white_lower, _white_upper
    _yellow_lower    = np.array(yellow_lower)
    _yellow_upper    = np.array(yellow_upper)
    _white_lower = np.array(white_lower)
    _white_upper = np.array(white_upper)

def get_hsv_bounds():
    return {
        'yellow_lower_h': int(_yellow_lower[0]),    'yellow_upper_h': int(_yellow_upper[0]),
        'yellow_lower_s': int(_yellow_lower[1]),    'yellow_upper_s': int(_yellow_upper[1]),
        'yellow_lower_v': int(_yellow_lower[2]),    'yellow_upper_v': int(_yellow_upper[2]),
        'white_lower_h':  int(_white_lower[0]), 'white_upper_h':  int(_white_upper[0]),
        'white_lower_s':  int(_white_lower[1]), 'white_upper_s':  int(_white_upper[1]),
        'white_lower_v':  int(_white_lower[2]), 'white_upper_v':  int(_white_upper[2]),
    }