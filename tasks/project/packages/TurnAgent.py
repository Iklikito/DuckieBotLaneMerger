import os
import time
import yaml
import numpy as np
from typing import Tuple
from tasks.project.packages.adjacent_lanes import AdjacentLane
from tasks.project.packages.detect_lane_markings import detect_lane_markings
from tasks.project.packages.settings import ROBOT_ID

_REENTRY_THRESHOLD = 400


def _get_config_path(robot_id):
    if robot_id.name == 'simulation':
        return 'config/turn_agent_config.yaml'
    return f'config/turn_agent_config.{robot_id.name}.yaml'


class TurnAgent:
    def __init__(self,
                 outgoing_lane: AdjacentLane = AdjacentLane.north):
        with open(_get_config_path(ROBOT_ID)) as f:
            cfg = yaml.safe_load(f)

        self._turn_start_time = time.time()
        self._frame = 0

        direction_key = outgoing_lane.name
        dir_cfg = cfg.get(direction_key, {})

        self._reentry_delay_s = float(dir_cfg.get('reentry_delay_s', 1.5))
        self._turn_speed      = float(dir_cfg.get('turn_speed', 0.2))
        self._turn_bias       = float(dir_cfg.get('turn_bias', 0.1))
        self.turn             = dir_cfg.get('turn', 'left')

    def compute_commands(self, image: np.ndarray) -> Tuple[float, float, bool]:
        print("Entered turn_agent.compute_commands frame", self._frame)
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
        print("Entered _check_reentry")
        mask_left, mask_right = detect_lane_markings(image)

        h = image.shape[0]
        roi_start = int(h * 0.75)

        yellow_pixels = int(np.count_nonzero(mask_left[roi_start:, :]))
        white_pixels  = int(np.count_nonzero(mask_right[roi_start:, :]))

        return (yellow_pixels + white_pixels) > _REENTRY_THRESHOLD