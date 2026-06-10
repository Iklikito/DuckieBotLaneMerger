import time
import cv2
import numpy as np

from tasks.project.packages.bot_state import BotState
from tasks.project.packages.adjacent_lanes import AdjacentLane
from tasks.project.packages.lane_state_decider import areEmptyLanesUntil
from tasks.project.packages.outgoing_lane_decider import decide_outgoing_lane
from tasks.project.packages.is_in_front_decider import is_in_front, get_red_mask, has_passed_red_line
from tasks.project.packages.convoy import convoy, calculate_distance_measure_to_leader
from tasks.project.packages.detect_lane_markings import detect_lane_markings
from tasks.project.packages.ObjectDetector import ObjectDetector
from tasks.project.packages.TurnAgent import TurnAgent
from tasks.project.packages._aux import get_next_state_and_set_leds, set_all_leds
from tasks.project.packages.LaneServoingAgent import LaneServoingAgent
from tasks.project.packages.settings import has_to_wait_predetermined, outgoing_lane_predetermined


def main(camera, wheels, leds, stop_event, debug=None, debug_lock=None, cmd_queue=None):
    print('[ProjectAgent] started main loop')

    def _update_debug(**kwargs):
        if debug is not None and debug_lock is not None:
            with debug_lock:
                debug.update(kwargs)

    outgoing_lane = outgoing_lane_predetermined
    if leds:
        leds.all_on()

    if outgoing_lane_predetermined is None or has_to_wait_predetermined:
        object_detector = ObjectDetector(
            config_path="config/object_detection_config.yaml",
            model_path="tasks/object_detection/models/best.onnx"
        )
        while not object_detector.model_loaded:
            time.sleep(1)
            print("Waiting for model to load...")
        print("Model loaded!")

    lane_servoing_agent = LaneServoingAgent(config_path="config/lane_servoing_config.yaml")
    print("Object detector and lane follower initialized.")

    bot_state = get_next_state_and_set_leds(state=None, leds=leds)
    printed_lr = False  # remove later
    waiting_for_red_line_to_disappear = False
    manual_drive = {'left': 0.0, 'right': 0.0}

    try:
        while not stop_event.is_set():
            ok, frame = camera.read()
            if not ok:
                time.sleep(0.05)
                continue

            # Drain any commands sent from the web UI# Drain any commands sent from the web UI
            if cmd_queue is not None:
                while not cmd_queue.empty():
                    cmd = cmd_queue.get_nowait()
                    key = cmd.get('key')
                    if key == 'remove_objects':
                        name_filter = str(cmd.get('value', '')).lower()
                        if name_filter and hasattr(wheels, 'remove_objects'):
                            wheels.remove_objects(name_filter)
                            print(f'[Agent] remove_objects: {name_filter}')
                    elif key == 'manual_drive':
                        manual_drive = cmd.get('value')
                        if manual_drive is None and cmd.get('reset_to_convoy', False):
                            bot_state = get_next_state_and_set_leds(state=None, leds=leds)
                            waiting_for_red_line_to_disappear = False

            # Always compute all masks fresh for the debug view
            red_mask = get_red_mask(frame)
            mask_left, mask_right = detect_lane_markings(frame)
            yellow_mask = (mask_left  * 255).astype(np.uint8)
            white_mask  = (mask_right * 255).astype(np.uint8)
            detected_objects = []

            # Manual drive overrides all FSM logic
            if manual_drive is not None:
                wheels.set_wheels_speed(manual_drive['left'], manual_drive['right'])
                _update_debug(
                    state='manual',
                    frame=frame.copy(),
                    red_mask=red_mask,
                    yellow_mask=yellow_mask,
                    white_mask=white_mask,
                    detections=[],
                )
                time.sleep(0.01)
                continue

            # Always compute all masks fresh for the debug view
            red_mask = get_red_mask(frame)
            mask_left, mask_right = detect_lane_markings(frame)
            yellow_mask = (mask_left  * 255).astype(np.uint8)
            white_mask  = (mask_right * 255).astype(np.uint8)
            detected_objects = []

            if bot_state == BotState.convoying:
                if is_in_front(frame):
                    waiting_for_red_line_to_disappear = True
                    #set_all_leds(leds, (1, 0, 1))

                if waiting_for_red_line_to_disappear and has_passed_red_line(frame):
                    bot_state = get_next_state_and_set_leds(bot_state, leds)
                    if outgoing_lane_predetermined is None:
                        outoing_lane = decide_outgoing_lane(frame, object_detector)
                    else:
                        outgoing_lane = outgoing_lane_predetermined
                    print(f"Outgoing lane: {outgoing_lane}")
                    wheels.set_wheels_speed(0.0, 0.0)
                else:
                    convoy(frame, wheels, leds)

            elif bot_state == BotState.waiting:
                if has_to_wait_predetermined:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    detected_objects = object_detector.detect(frame_rgb) or []
                    print("Waiting...")
                    print(f"Detected objects: {detected_objects}")
                    can_merge = areEmptyLanesUntil(outgoing_lane, detected_objects)
                else:
                    bot_state = get_next_state_and_set_leds(bot_state, leds)
                    turn_agent = TurnAgent(outgoing_lane)
                    print("Switched to turning...")
                    continue

                print(f"Can merge: {can_merge}")

                if can_merge:
                    time.sleep(0.5)
                    can_merge = areEmptyLanesUntil(outgoing_lane, detected_objects)
                    print(f"Can merge: {can_merge}")
                    if can_merge:
                        bot_state = get_next_state_and_set_leds(bot_state, leds)
                        turn_agent = TurnAgent(outgoing_lane)
                        print("Switched to turning...")

            elif bot_state == BotState.turning:
                print("Calling turn_agent.step")
                left, right, reentered = turn_agent.step(frame)
                if not printed_lr:
                    print(f"Turning: left={left}, right={right}")
                    printed_lr = True

                wheels.set_wheels_speed(left, right)

                if reentered:
                    continue
                    print("Reentry detected, finishing.")
                    bot_state = get_next_state_and_set_leds(bot_state, leds)
                    wheels.set_wheels_speed(0.0, 0.0)

            elif bot_state == BotState.finishing:
                pass

            else:
                raise ValueError(f"Invalid bot state: {bot_state}")

            distance_measure = None
            try:
                distance_measure = calculate_distance_measure_to_leader(frame)
            except Exception:
                distance_measure = None

            _update_debug(
                state=bot_state.name,
                frame=frame.copy(),
                red_mask=red_mask,
                yellow_mask=yellow_mask,
                white_mask=white_mask,
                detections=detected_objects,
                distance_measure=distance_measure,
            )

            time.sleep(0.01)

    finally:
        print("hi2")
        wheels.set_wheels_speed(0.0, 0.0)
        if leds:
            leds.all_off()
