import cv2
import numpy as np


def get_red_mask(frame) -> np.ndarray:
    """Return a binary mask of red pixels in the bottom quarter of the frame."""
    h   = frame.shape[0]
    roi = frame[int(h * 0.75):, :]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0,   120, 100]), np.array([10,  255, 255]))
    mask2 = cv2.inRange(hsv, np.array([170, 120, 100]), np.array([180, 255, 255]))
    combined = mask1 | mask2

    # Pad back to full frame height so the visualizer can overlay it directly
    full = np.zeros(frame.shape[:2], dtype=np.uint8)
    full[int(h * 0.75):, :] = combined
    return full


def is_in_front(frame) -> bool:
    return int(np.count_nonzero(get_red_mask(frame))) > 600