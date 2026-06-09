import time
import yaml
import numpy as np
from typing import Tuple
from tasks.project.packages.adjacent_lanes import AdjacentLane 
from tasks.project.packages.detect_lane_markings import detect_lane_markings
from tasks.project.packages._aux import get_turn_agent_config_path
from tasks.project.packages.settings import ROBOT_ID

_REENTRY_THRESHOLD = 600

class TurnAgent:
    def __init__(self,
                 outgoing_lane: AdjacentLane = AdjacentLane.north):
        with open(get_turn_agent_config_path(ROBOT_ID)) as f:
            cfg = yaml.safe_load(f)

        self._reentry_delay_s = float(cfg.get('reentry_delay_s', 1.5))
        self._turn_start_time = time.time()
        self._frame = 0

        direction_key = outgoing_lane.name
        dir_cfg = cfg.get(direction_key, {})

        self._turn_speed = float(dir_cfg.get('turn_speed', 0.2))
        self._turn_bias = float(dir_cfg.get('turn_bias', 0.1))

        if outgoing_lane == AdjacentLane.east:
            self._turn_speed = 0.2
            self._turn_bias = 0.125
            self.turn = 'right'

        elif outgoing_lane == AdjacentLane.north:
            self._turn_speed = 0.18
            self._turn_bias = 0.03
            self.turn = 'left'

        elif outgoing_lane == AdjacentLane.west:
            self._turn_speed = 0.2
            self._turn_bias = 0.12
            self.turn = 'left'
 
    def step(self, image: np.ndarray) -> Tuple[float, float]:
        print("Enterd turn_agent.step function frame")
        self._frame += 1
 
        if self.turn == 'right':
            left  = float(np.clip(self._turn_speed + self._turn_bias, 0.0, 1.0))
            right = float(np.clip(self._turn_speed - self._turn_bias, 0.0, 1.0))
        else:
            left  = float(np.clip(self._turn_speed - self._turn_bias, 0.0, 1.0))
            right = float(np.clip(self._turn_speed + self._turn_bias, 0.0, 1.0))
 
        if time.time() - self._turn_start_time < self._reentry_delay_s:
            return left, right, False

        print("Calling _check_reentry")
        reentered = self._check_reentry(image)
        return left, right, reentered

    def _check_reentry(self, image: np.ndarray) -> bool:
        print("Entered _check_reentry function frame")
        mask_left, mask_right = detect_lane_markings(image)
 
        h = image.shape[0]
        roi_start = int(h * 0.75)
 
        yellow_pixels = int(np.count_nonzero(mask_left[roi_start:, :]))
        white_pixels  = int(np.count_nonzero(mask_right[roi_start:, :]))
 
        return (yellow_pixels + white_pixels) > _REENTRY_THRESHOLD