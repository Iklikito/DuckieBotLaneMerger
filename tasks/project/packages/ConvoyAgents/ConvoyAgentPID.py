import time
import numpy as np
from typing import Tuple

from tasks.project.packages.FrameDictionary import FrameDictionary
from tasks.project.packages.LaneServoingAgent import LaneServoingAgent

from tasks.project.packages.ConvoyAgents.distance_measurer import calculate_distance_measure_to_leader

class ConvoyAgentPID:
    """
    Maintains a fixed following distance using a PID controller on the distance error.
    The base speed is driven by the PID output; steering comes from the lane servoing agent.

    Distance measure: mean nearest-neighbour distance between circle grid points (pixels).
    Larger value → further away. Setpoint is the target distance measure.

    Parameters
    ──────────
    setpoint        target distance measure (pixels)
    kp, ki, kd      PID gains
    max_speed       forward speed ceiling
    fallback_speed  speed used when the leader is not detected
    """

    def __init__(self,
                 setpoint:       float = 40.0,
                 kp:             float = 0.005,
                 ki:             float = 0.0001,
                 kd:             float = 0.001,
                 max_speed:      float = 0.4,
                 fallback_speed: float = 0.2):
        self.setpoint       = setpoint
        self.kp             = kp
        self.ki             = ki
        self.kd             = kd
        self.max_speed      = max_speed
        self.fallback_speed = fallback_speed

        self._integral   = 0.0
        self._prev_error = 0.0
        self._t_prev     = time.time()

    def compute_commands(self, frame: FrameDictionary, lane_follower: LaneServoingAgent) -> Tuple[float, float]:
        distance = calculate_distance_measure_to_leader(frame)

        if distance is None:
            # Leader not detected — hold fallback speed, reset derivative, don't wind up integral
            self._prev_error = 0.0
            self._t_prev     = time.time()
            left_s, right_s  = lane_follower.get_commands()
            steering         = (right_s - left_s) / 2.0
            base             = self.fallback_speed
            return float(np.clip(base - steering, 0.0, 1.0)), float(np.clip(base + steering, 0.0, 1.0))

        now = time.time()
        dt  = max(now - self._t_prev, 1e-4)
        self._t_prev = now

        # Positive error → too far → speed up; negative → too close → slow down
        error            = distance - self.setpoint
        self._integral  += error * dt
        derivative       = (error - self._prev_error) / dt
        self._prev_error = error

        base = float(np.clip(
            self.kp * error + self.ki * self._integral + self.kd * derivative,
            0.0,
            self.max_speed,
        ))

        # Blend PID base speed with lane servoing steering
        left_s, right_s = lane_follower.get_commands()
        steering        = (right_s - left_s) / 2.0

        left  = float(np.clip(base - steering, 0.0, 1.0))
        right = float(np.clip(base + steering, 0.0, 1.0))
        return left, right