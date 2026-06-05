import cv2
import numpy as np


def get_red_mask(frame) -> np.ndarray:
    """Return a binary mask of red pixels in the entire frame."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

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

    return mask1 | mask2


def is_in_front(frame) -> bool:
    mask = get_red_mask(frame)

    h = mask.shape[0]
    bottom_quarter = mask[int(h * 0.75):, :]

    return int(np.count_nonzero(bottom_quarter)) > 1600