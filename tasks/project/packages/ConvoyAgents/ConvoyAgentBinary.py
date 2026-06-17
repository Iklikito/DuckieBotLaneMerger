from typing import Tuple

from tasks.project.packages.FrameDictionary import FrameDictionary
from tasks.project.packages.LaneServoingAgent import LaneServoingAgent

from tasks.project.packages.ConvoyAgents.distance_measurer import calculate_distance_measure_to_leader

_distance_threshold = 40


def get_distance_threshold() -> float:
    return _distance_threshold


def set_distance_threshold(value: float):
    global _distance_threshold
    _distance_threshold = float(value)


class ConvoyAgentBinary:
    """
    Moves at a fixed speed when the leader is far enough away, stops otherwise.
    """

    def __init__(self, fixed_speed: float = 0.2):
        self.fixed_speed = fixed_speed

    def compute_commands(self, frame: FrameDictionary, lane_follower: LaneServoingAgent) -> Tuple[float, float]:
        distance = calculate_distance_measure_to_leader(frame)
        if distance is not None and distance < get_distance_threshold():
            return 0.0, 0.0
        return lane_follower.get_commands()