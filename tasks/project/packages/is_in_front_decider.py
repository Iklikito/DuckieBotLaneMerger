import cv2
import numpy as np

def is_in_front(frame: np.ndarray) -> bool:
    h = frame.shape[0]
    roi = frame[int(h * 0.75):, :]

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    mask1 = cv2.inRange(
        hsv,
        np.array([0, 120, 100]),
        np.array([10, 255, 255])
    )

    mask2 = cv2.inRange(
        hsv,
        np.array([170, 120, 100]),
        np.array([180, 255, 255])
    )

    mask = mask2

    return np.count_nonzero(mask) > 1600