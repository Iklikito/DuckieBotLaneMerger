import os
import time
import yaml
import numpy as np
from typing import Tuple
from tasks.project.packages.adjacent_lanes import AdjacentLane
from tasks.project.packages.detect_lane_markings import detect_lane_markings
from tasks.project.packages.settings import ROBOT_ID

_REENTRY_THRESHOLD = 400
_N_TOT   = 135        # ticks per revolution
_R       = 0.025      # wheel radius (m)
_L       = 0.9        # baseline (m), half = 0.05


def _get_config_path(robot_id):
    if robot_id.name == 'simulation':
        return 'config/turn_agent_p_config.yaml'
    return f'config/turn_agent_p_config.{robot_id.name}.yaml'


class TurnAgentPID:
    def __init__(self,
                 outgoing_lane: AdjacentLane = AdjacentLane.north,
                 wheels=None):
        with open(_get_config_path(ROBOT_ID)) as f:
            cfg = yaml.safe_load(f)

        if wheels is None or not hasattr(wheels, 'encoders') or wheels.encoders is None:
            raise RuntimeError('TurnAgentP requires wheel encoders — use TurnAgent as fallback')

        self._wheels = wheels
        self._frame  = 0

        direction_key = outgoing_lane.name
        dir_cfg = cfg.get(direction_key, {})

        self.turn          = dir_cfg.get('turn', 'left')
        self._v            = float(dir_cfg.get('speed', 0.3))
        self._kp           = float(dir_cfg.get('kp', 5.0))
        self._ki           = float(dir_cfg.get('ki', 0.2))
        self._kd           = float(dir_cfg.get('kd', 0.1))
        self._is_straight  = bool(dir_cfg.get('straight', False))

        # Arc geometry
        inner_radius = float(dir_cfg.get('inner_radius', 0.18))
        outer_radius = float(dir_cfg.get('outer_radius', 0.27))
        self._arc_radius   = (inner_radius + outer_radius) / 2.0  # center of bot

        # Target heading change: +π/2 left, -π/2 right, 0 straight
        if self._is_straight:
            self._target_dtheta = 0.0
        elif self.turn == 'left':
            self._target_dtheta = np.pi / 2
        else:
            self._target_dtheta = -np.pi / 2

        # Odometry state — starts at origin facing forward
        self._x     = 0.0
        self._y     = 0.0
        self._theta = 0.0

        # PID state
        self._e_int  = 0.0
        self._e_prev = 0.0
        self._t_prev = time.time()

        # Encoder baseline
        self._prev_ticks_l = wheels.encoders.left.ticks
        self._prev_ticks_r = wheels.encoders.right.ticks

        # Arc is done when heading change reaches target
        self._arc_done = False

    # ── Odometry ──────────────────────────────────────────────────────────────

    def _update_odometry(self):
        ticks_l = self._wheels.encoders.left.ticks
        ticks_r = self._wheels.encoders.right.ticks

        delta_ticks_l = ticks_l - self._prev_ticks_l
        delta_ticks_r = ticks_r - self._prev_ticks_r
        self._prev_ticks_l = ticks_l
        self._prev_ticks_r = ticks_r

        d_l = _R * (delta_ticks_l / _N_TOT) * 2 * np.pi
        d_r = _R * (delta_ticks_r / _N_TOT) * 2 * np.pi

        d_A    = (d_r + d_l) / 2.0
        dtheta = (d_r - d_l) / _L

        self._x     += d_A * np.cos(self._theta)
        self._y     += d_A * np.sin(self._theta)
        self._theta += dtheta

    # ── Target heading at current arc progress ─────────────────────────────

    def _target_heading(self) -> float:
        """
        For a circular arc: heading at progress s along the arc equals
        initial heading (0) + s / arc_radius.
        We use current heading as proxy for progress.
        Target heading is just the cumulative heading change so far
        clamped to the final target.
        """
        if self._is_straight:
            return 0.0
        sign = 1 if self.turn == 'left' else -1
        progress = abs(self._theta) / abs(self._target_dtheta)
        progress = min(progress, 1.0)
        return sign * progress * abs(self._target_dtheta)

    # ── PID on heading error ───────────────────────────────────────────────

    def _compute_omega(self) -> float:
        t_now = time.time()
        dt    = max(t_now - self._t_prev, 1e-4)
        self._t_prev = t_now

        theta_ref = self._target_heading()
        e         = theta_ref - self._theta

        self._e_int += e * dt
        e_der        = (e - self._e_prev) / dt
        self._e_prev = e

        return self._kp * e + self._ki * self._e_int + self._kd * e_der

    # ── (v, ω) → wheel speeds ─────────────────────────────────────────────

    def _to_wheel_speeds(self, v: float, omega: float) -> Tuple[float, float]:
        left  = v - omega * (_L / 2.0)
        right = v + omega * (_L / 2.0)
        # Normalise if either exceeds 1.0
        max_speed = max(abs(left), abs(right), 1.0)
        left  /= max_speed
        right /= max_speed
        return float(np.clip(left, -1.0, 1.0)), float(np.clip(right, -1.0, 1.0))

    # ── Arc completion check ───────────────────────────────────────────────

    def _arc_reached(self) -> bool:
        if self._is_straight:
            # Use distance travelled as proxy
            dist = np.sqrt(self._x**2 + self._y**2)
            return dist >= self._arc_radius  # reuse arc_radius as straight distance
        return abs(self._theta) >= abs(self._target_dtheta)

    # ── Public interface ───────────────────────────────────────────────────

    def compute_commands(self, image: np.ndarray) -> Tuple[float, float, bool]:
        print(f"Entered TurnAgentP.compute_commands frame {self._frame}")
        self._frame += 1

        self._update_odometry()
        omega        = self._compute_omega()
        left, right  = self._to_wheel_speeds(self._v, omega)

        if not self._arc_reached():
            return left, right, False

        print("Calling _check_reentry")
        reentered = self._check_reentry(image)
        return left, right, reentered

    def _check_reentry(self, image: np.ndarray) -> bool:
        print("Entered _check_reentry")
        mask_left, mask_right = detect_lane_markings(image)

        h         = image.shape[0]
        roi_start = int(h * 0.75)

        yellow_pixels = int(np.count_nonzero(mask_left[roi_start:, :]))
        white_pixels  = int(np.count_nonzero(mask_right[roi_start:, :]))

        return (yellow_pixels + white_pixels) > _REENTRY_THRESHOLD