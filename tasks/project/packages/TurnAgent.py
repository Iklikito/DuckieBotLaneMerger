import numpy as np
from typing import Tuple
from tasks.project.packages.adjacent_lanes import AdjacentLane 
 
class TurnAgent:
    def __init__(self,
                 outgoing_lane: AdjacentLane = AdjacentLane.north):
        self._frame = 0

        if outgoing_lane == AdjacentLane.east:
            self._turn_speed = 0.18
            self._turn_bias = 0.05
            self.turn = 'right'

        elif outgoing_lane == AdjacentLane.north:
            self._turn_speed = 0.2
            self._turn_bias = 0.0
            self.turn = 'straight'

        elif outgoing_lane == AdjacentLane.west:
            self._turn_speed = 0.2
            self._turn_bias = 0.02
            self.turn = 'left'
 
    def step(self, image: np.ndarray) -> Tuple[float, float]:
        self._frame += 1
 
        if self.turn == 'right':
            left  = float(np.clip(self._turn_speed + self._turn_bias, 0.0, 1.0))
            right = float(np.clip(self._turn_speed - self._turn_bias, 0.0, 1.0))
        else:
            left  = float(np.clip(self._turn_speed - self._turn_bias, 0.0, 1.0))
            right = float(np.clip(self._turn_speed + self._turn_bias, 0.0, 1.0))
 
        self._check_reentry(image)
        return left, right

    def _check_reentry(self, image: np.ndarray) -> None:
        # Placeholder so the turn agent can run without an implementation.
        return None