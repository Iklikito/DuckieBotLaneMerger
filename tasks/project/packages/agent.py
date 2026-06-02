import time
import cv2
import numpy as np
from tasks.project.packages.bot_state import BotState
from tasks.project.packages.adjacent_lanes import AdjacentLane
from tasks.project.packages.lane_state_decider import areEmptyLanesUntil
from tasks.project.packages.outgoing_lane_decider import decide_outgoing_lane
from tasks.project.packages.is_in_front_decider import is_in_front
from tasks.project.packages.convoy import convoy
from tasks.project.packages.ObjectDetector import ObjectDetector
from tasks.project.packages.TurnAgent import TurnAgent
from tasks.project.packages._aux import set_all_leds

def main(camera, wheels, leds, stop_event):
    print('[ProjectAgent] started main loop')

    print("hi0")
    bot_state = BotState.convoying
    set_all_leds(leds, 1, 0, 0)
    outgoing_lane = None
    object_detector = ObjectDetector(config_path="config/object_detection_config.yaml", model_path="tasks/object_detection/models/best.onnx")
    print("hi1")

    try:
        while not stop_event.is_set():
            ok, frame = camera.read()
            if not ok:
                time.sleep(0.05)
                continue

            print(f"Current bot state: {bot_state}")

            if bot_state == BotState.convoying:
                set_all_leds(leds, 1, 0, 0)
                if is_in_front(frame):
                    print("Bot is in front of the lane, now waiting")
                    bot_state = BotState.waiting
                    outgoing_lane = decide_outgoing_lane(frame, object_detector)
                    set_all_leds(leds, 0, 1, 0)
                else:
                    convoy(frame, wheels, leds)

            elif bot_state == BotState.waiting:
                detected_objects = object_detector.detect(frame)
                can_go = areEmptyLanesUntil(outgoing_lane, frame, detected_objects)

                if can_go:
                    time.sleep(300)
                    can_go = areEmptyLanesUntil(outgoing_lane, frame, detected_objects)
                    if can_go:
                        print("Right lanes are clear, starting to turn")
                        bot_state = BotState.turning
                        turn_agent = TurnAgent(outgoing_lane)
                        set_all_leds(leds, 0, 0, 1)

            elif bot_state == BotState.turning:
                left, right = turn_agent.step(frame)
                wheels.set_wheels_speed(left, right)
                print("Turning...")

            elif bot_state == BotState.finishing:
                pass # TODO

            else:
                raise ValueError(f"Invalid bot state: {bot_state}")

            time.sleep(0.01)
    finally:
        print("hi2")
        wheels.set_wheels_speed(0.0, 0.0)
        if leds:
            leds.all_off()
