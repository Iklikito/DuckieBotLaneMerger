import numpy as np
import cv2
from typing import Optional

from tasks.project.packages.FrameDictionary import FrameDictionary

def calculate_distance_measure_to_leader(frame: FrameDictionary) -> Optional[float]:
    found, centers = cv2.findCirclesGrid(frame.gray, (7, 3), flags=cv2.CALIB_CB_SYMMETRIC_GRID)
    if not found or centers is None:
        return None
    pts = centers.reshape(-1, 2)
    d = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=2)
    np.fill_diagonal(d, np.inf)
    return float(np.mean(np.min(d, axis=1)))