import time
import cv2
import numpy as np
from typing import Optional

from tasks.project.packages.bot_state import BotState
from tasks.project.packages.adjacent_lanes import AdjacentLane
from tasks.project.packages.lane_state_decider import areEmptyLanesUntil
from tasks.project.packages.outgoing_lane_decider import decide_outgoing_lane
from tasks.project.packages.is_in_front_decider import is_in_front, get_red_mask, has_passed_red_line
from tasks.project.packages.convoy import convoy, calculate_distance_measure_to_leader
from tasks.project.packages.detect_lane_markings import detect_lane_markings
from tasks.project.packages.ObjectDetector import ObjectDetector
from tasks.project.packages.TurnAgent import TurnAgent
from tasks.project.packages.TurnAgentP import TurnAgentP
from tasks.project.packages._aux import get_next_state_and_set_leds, set_all_leds
from tasks.project.packages.LaneServoingAgent import LaneServoingAgent
from tasks.project.packages.settings import has_to_wait_predetermined, outgoing_lane_predetermined, start_in_manual_drive, use_p_turn_agent, color_coded_leds

# Module-level outgoing lane override — readable/writable by real_server via get/set
_outgoing_lane_override = outgoing_lane_predetermined


def get_outgoing_lane():
    v = _outgoing_lane_override
    return v.name if v is not None else None


def set_outgoing_lane(val):
    global _outgoing_lane_override
    _outgoing_lane_override = AdjacentLane[val] if val is not None else None


def main(camera, wheels, leds, stop_event, debug=None, debug_lock=None, cmd_queue=None):
    print('[ProjectAgent] started main loop')

    def _update_debug(**kwargs):
        if debug is not None and debug_lock is not None:
            with debug_lock:
                debug.update(kwargs)

    if color_coded_leds and leds:
        leds.all_on()

    needs_detector = _outgoing_lane_override is None or has_to_wait_predetermined
    if needs_detector:
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
    manual_drive = {'left': 0.0, 'right': 0.0} if start_in_manual_drive else None
    outgoing_lane = None

    try:
        while not stop_event.is_set():
            ok, frame_bgr = camera.read()
            if not ok:
                time.sleep(0.05)
                continue

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

            # Drain any commands sent from the web UI
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
            red_mask = get_red_mask(frame_bgr)
            mask_left, mask_right = detect_lane_markings(frame_bgr)
            yellow_mask = (mask_left  * 255).astype(np.uint8)
            white_mask  = (mask_right * 255).astype(np.uint8)
            detected_objects = []

            # Manual drive overrides all FSM logic
            if manual_drive is not None:
                wheels.set_wheels_speed(manual_drive['left'], manual_drive['right'])
                _update_debug(
                    state='manual',
                    frame=frame_bgr.copy(),
                    red_mask=red_mask,
                    yellow_mask=yellow_mask,
                    white_mask=white_mask,
                    detections=[],
                    lane_debug=None,
                )
                time.sleep(0.01)
                continue

            if bot_state == BotState.convoying:
                if is_in_front(frame_bgr):
                    waiting_for_red_line_to_disappear = True

                if waiting_for_red_line_to_disappear and has_passed_red_line(frame_bgr):
                    bot_state = get_next_state_and_set_leds(bot_state, leds)
                    if _outgoing_lane_override is None:
                        outgoing_lane = decide_outgoing_lane(frame_rgb, object_detector)
                    else:
                        outgoing_lane = _outgoing_lane_override
                    print(f"Outgoing lane: {outgoing_lane}")
                    wheels.set_wheels_speed(0.0, 0.0)
                else:
                    left, right = convoy(frame_rgb, lane_servoing_agent, use_lane_follower=not waiting_for_red_line_to_disappear)
                    wheels.set_wheels_speed(left, right)

            elif bot_state == BotState.waiting:
                if has_to_wait_predetermined:
                    detected_objects = object_detector.detect(frame_rgb) or []
                    print("Waiting...")
                    print(f"Detected objects: {detected_objects}")
                    can_merge = areEmptyLanesUntil(outgoing_lane, detected_objects)
                else:
                    bot_state = get_next_state_and_set_leds(bot_state, leds)
                    if use_p_turn_agent:
                        turn_agent = TurnAgentP(outgoing_lane, wheels)
                    else:
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
                        if use_p_turn_agent:
                            turn_agent = TurnAgentP(outgoing_lane, wheels)
                        else:
                            turn_agent = TurnAgent(outgoing_lane)
                        print("Switched to turning...")

            elif bot_state == BotState.turning:
                print("Calling turn_agent.compute_commands")
                left, right, reentered = turn_agent.compute_commands(frame_bgr)
                if not printed_lr:
                    print(f"Turning: left={left}, right={right}")
                    printed_lr = True

                wheels.set_wheels_speed(left, right)

                if reentered:
                    print("Reentry detected, finishing.")
                    bot_state = get_next_state_and_set_leds(bot_state, leds)
                    wheels.set_wheels_speed(0.0, 0.0)

            elif bot_state == BotState.finishing:
                left, right = lane_servoing_agent.compute_commands(frame_rgb)
                wheels.set_wheels_speed(left, right)

            else:
                raise ValueError(f"Invalid bot state: {bot_state}")

            distance_measure = None
            try:
                distance_measure = calculate_distance_measure_to_leader(frame_bgr)
            except Exception:
                distance_measure = None

            _update_debug(
                state=bot_state.name,
                frame=frame_bgr.copy(),
                red_mask=red_mask,
                yellow_mask=yellow_mask,
                white_mask=white_mask,
                detections=detected_objects,
                distance_measure=distance_measure,
                lane_debug=lane_servoing_agent.last_debug_info,
            )

            time.sleep(0.01)

    finally:
        print("hi2")
        wheels.set_wheels_speed(0.0, 0.0)
        if leds:
            leds.all_off()