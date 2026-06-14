import numpy as np
import cv2
from typing import Tuple

distance_measure_threshold = 25


def get_distance_threshold() -> float:
    return distance_measure_threshold


def set_distance_threshold(value: float):
    global distance_measure_threshold
    distance_measure_threshold = float(value)

def calculate_distance_measure_to_leader(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    found, centers = cv2.findCirclesGrid(gray, (7,3), flags=cv2.CALIB_CB_SYMMETRIC_GRID)
    if not found or centers is None:
        return None

    pts = centers.reshape(-1, 2)
    d = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=2)
    np.fill_diagonal(d, np.inf)
    return float(np.mean(np.min(d, axis=1)))

def safe_to_move(frame):
    distance = calculate_distance_measure_to_leader(frame)
    return distance is None or distance >= distance_measure_threshold

def convoy(frame, lane_follower, use_lane_follower) -> Tuple[float, float]:
    if not safe_to_move(frame):
        return 0.0, 0.0
    if use_lane_follower:
        return lane_follower.compute_commands(frame)
    return 0.2, 0.2