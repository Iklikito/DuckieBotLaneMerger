import time

from tasks.project.packages.bot_state import BotState
from tasks.project.packages.adjacent_lanes import AdjacentLane
from tasks.project.packages.lane_state_decider import areEmptyLanesUntil
from tasks.project.packages.outgoing_lane_decider import decide_outgoing_lane
from tasks.project.packages.is_in_front_decider import is_in_front
from tasks.project.packages.convoy import convoy
from tasks.project.packages.ObjectDetector import ObjectDetector
from tasks.project.packages.TurnAgent import TurnAgent
from tasks.project.packages._aux import get_next_state_and_set_leds
from tasks.project.packages.LaneServoingAgent import LaneServoingAgent

def main(camera, wheels, leds, stop_event):
    print('[ProjectAgent] started main loop')

    bot_state = get_next_state_and_set_leds(state=None, leds=leds)
    outgoing_lane = None
    object_detector = ObjectDetector(config_path="config/object_detection_config.yaml", model_path="tasks/object_detection/models/best.onnx")
    lane_servoing_agent = LaneServoingAgent(config_path="config/lane_servoing_config.yaml")
    print("Object detector and lane follower initialized.")

    try:
        while not stop_event.is_set():
            ok, frame = camera.read()
            if not ok:
                time.sleep(0.05)
                continue

            if bot_state == BotState.convoying:
                if is_in_front(frame):
                    bot_state = get_next_state_and_set_leds(bot_state, leds)
                    outgoing_lane = decide_outgoing_lane(frame, object_detector)
                    wheels.set_wheels_speed(0.0, 0.0)
                else:
                    pass
                    #convoy(frame, wheels, leds)

            elif bot_state == BotState.waiting:
                detected_objects = object_detector.detect(frame)
                can_merge = areEmptyLanesUntil(outgoing_lane, frame, detected_objects)

                if can_merge:
                    time.sleep(0.5)
                    can_merge = areEmptyLanesUntil(outgoing_lane, frame, detected_objects)
                    if can_merge:
                        bot_state = get_next_state_and_set_leds(bot_state, leds)
                        turn_agent = TurnAgent(outgoing_lane)

            elif bot_state == BotState.turning:
                left, right = turn_agent.step(frame)
                wheels.set_wheels_speed(left, right)
                print("Turning...")

            elif bot_state == BotState.finishing:
                print("Finishing...")

            else:
                raise ValueError(f"Invalid bot state: {bot_state}")

            time.sleep(0.01)
    finally:
        print("hi2")
        wheels.set_wheels_speed(0.0, 0.0)
        if leds:
            leds.all_off()
