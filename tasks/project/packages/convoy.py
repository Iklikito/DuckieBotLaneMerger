import numpy as np
import cv2

distance_measure_threshold = 50

def calculate_distance_measure_to_leader(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    found, centers = cv2.findCirclesGrid(gray, (7,3), flags=cv2.CALIB_CB_SYMMETRIC_GRID)
    if not found or centers is None:
        return None

    pts = centers.reshape(-1, 2)
    d = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=2)
    np.fill_diagonal(d, np.inf)
    return float(np.mean(np.min(d, axis=1)))

def convoy(frame, wheels, leds, lane_follower):
    distance = calculate_distance_measure_to_leader(frame)
    safe_to_move = distance is not None and distance < distance_measure_threshold

    if safe_to_move:
        left = 0.0
        right = 0.0
        wheels.set_wheels_speed(0.0, 0.0)
    else:
        left, right = lane_follower.compute_commands(frame)
        wheels.set_wheels_speed(left, right)