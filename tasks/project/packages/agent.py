import time
import cv2

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

    outgoing_lane = None
    if leds:
        leds.all_on()
    object_detector = ObjectDetector(config_path="config/object_detection_config.yaml", model_path="tasks/object_detection/models/best.onnx")
    while not object_detector.model_loaded:
        time.sleep(1)
        print("Waiting for model to load...")
        print(f"object_detector.trt_building: {object_detector.trt_building}")
        print(f"object_detector.load_error: {object_detector.load_error}")
    print("Model loaded!")
    lane_servoing_agent = LaneServoingAgent(config_path="config/lane_servoing_config.yaml")
    print("Object detector and lane follower initialized.")

    bot_state = get_next_state_and_set_leds(state=None, leds=leds)
    printed_lr = False # remove later

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
                    print(f"Outgoing lane: {outgoing_lane}")
                    wheels.set_wheels_speed(0.0, 0.0)
                else:
                    pass
                    wheels.set_wheels_speed(0.1,0.1)
                    #convoy(frame, wheels, leds)

            elif bot_state == BotState.waiting:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if object_detector.model_loaded:
                    print("Object detector model was loaded")
                else:
                    print("Object detector model was not loaded")
                detected_objects = object_detector.detect(frame_rgb)
                if object_detector.model_loaded:
                    print("Object detector model was loaded")
                else:
                    print("Object detector model was not loaded")
                can_merge = areEmptyLanesUntil(outgoing_lane, detected_objects)

                if can_merge:
                    time.sleep(0.5)
                    can_merge = areEmptyLanesUntil(outgoing_lane, detected_objects)
                    if can_merge:
                        bot_state = get_next_state_and_set_leds(bot_state, leds)
                        turn_agent = TurnAgent(outgoing_lane)

            elif bot_state == BotState.turning:
                left, right = turn_agent.step(frame)
                if not printed_lr:
                    print(f"Turning: left={left}, right={right}")
                    printed_lr=True
                #wheels.set_wheels_speed(left, right)

            elif bot_state == BotState.finishing:
                pass

            else:
                raise ValueError(f"Invalid bot state: {bot_state}")

            time.sleep(0.01)
    finally:
        print("hi2")
        wheels.set_wheels_speed(0.0, 0.0)
        if leds:
            leds.all_off()
