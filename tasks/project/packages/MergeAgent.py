import time

from tasks.project.packages.adjacent_lanes                 import AdjacentLane
from tasks.project.packages.bot_state                      import BotState
from tasks.project.packages.ConvoyAgents.ConvoyAgentBinary import ConvoyAgentBinary
from tasks.project.packages.ConvoyAgents.ConvoyAgentPID    import ConvoyAgentPID
from tasks.project.packages.ConvoyAgents.distance_measurer import calculate_distance_measure_to_leader
from tasks.project.packages.detect_lane_markings           import detect_lane_markings
from tasks.project.packages.is_in_front_decider            import is_in_front, get_red_mask, has_passed_red_line
from tasks.project.packages.lane_state_decider             import areEmptyLanesUntil
from tasks.project.packages.LaneServoingAgent              import LaneServoingAgent, register_live_agent
from tasks.project.packages.ObjectDetector                 import ObjectDetector, register_live_detector
from tasks.project.packages.outgoing_lane_decider          import decide_outgoing_lane, recheck_outgoing_lane
from tasks.project.packages.TurnAgents.TurnAgentOpenLoop   import TurnAgentOpenLoop
from tasks.project.packages.TurnAgents.TurnAgentPID        import TurnAgentPID
from tasks.project.packages.FrameDictionary                import FrameDictionary
from tasks.project.packages.settings                       import (
    color_coded_leds, debugging, has_to_wait_predetermined, merge_check_interval_s,
    outgoing_lane_predetermined, required_merge_confirmations, ROBOT_ID,
    start_in_manual_drive, use_pid_turn_agent, use_pid_convoy_agent,
)
from tasks.project.packages._aux                           import (
    debug_print, get_next_state,
    get_state_entrance_console_message, set_front_leds, state_to_led_color,
)

# Module-level outgoing lane override — readable/writable by real_server via get/set
_outgoing_lane_override = outgoing_lane_predetermined


def get_outgoing_lane():
    v = _outgoing_lane_override
    return v.name if v is not None else None


def set_outgoing_lane(val):
    global _outgoing_lane_override
    _outgoing_lane_override = AdjacentLane[val] if val is not None else None


class MergeAgent:
    def __init__(self, camera, wheels, leds, stop_event, debug, debug_lock, cmd_queue):
        self.camera     = camera
        self.wheels     = wheels
        self.leds       = leds
        self.stop_event = stop_event
        self.debug      = debug
        self.debug_lock = debug_lock
        self.cmd_queue  = cmd_queue

        self._initialize_agents()

        self.frame = FrameDictionary(None)
        self.manual_drive = {'left': 0.0, 'right': 0.0} if start_in_manual_drive else None

        # Inter-state variables (produced by one state, consumed by the next)
        self.outgoing_lane = None   # set at end of convoying, used in waiting + turning
        self.turn_agent    = None   # set at end of waiting, used in turning

        self.state = None
        self._transition_to_next()  # None → convoying

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        try:
            while not self.stop_event.is_set():
                if not self._update_frame():
                    continue
                self._drain_commands()
                self._compute_debug_masks()

                self.lane_servoing_agent.process(self.frame)

                if self.manual_drive is not None:
                    self._handle_manual()
                    continue

                self._step_fsm()
                self._update_debug()
                time.sleep(0.01)

        finally:
            self.wheels.set_wheels_speed(0.0, 0.0)
            if self.leds:
                self.leds.all_off()

    # ── FSM dispatch ──────────────────────────────────────────────────────────

    def _step_fsm(self):
        {
            BotState.convoying: self._handle_convoying,
            BotState.waiting:   self._handle_waiting,
            BotState.turning:   self._handle_turning,
            BotState.finishing: self._handle_finishing,
        }[self.state]()

    # ── State handlers ────────────────────────────────────────────────────────

    def _handle_convoying(self):
        if is_in_front(self.frame):
            self.waiting_for_red_line_to_disappear = True

        if self.waiting_for_red_line_to_disappear and has_passed_red_line(self.frame):
            if _outgoing_lane_override is None:
                detected_objects = self.object_detector.detect(self.frame) or []
                self.outgoing_lane = decide_outgoing_lane(detected_objects)
            else:
                self.outgoing_lane = _outgoing_lane_override
            debug_print(f"Outgoing lane: {self.outgoing_lane}", debugging)
            self.wheels.set_wheels_speed(0.0, 0.0)
            self._transition_to_next()
        else:
            if not self.waiting_for_red_line_to_disappear:
                left, right = self.convoy_agent.compute_commands(self.frame, self.lane_servoing_agent)
            else:
                left, right = 0.2, 0.2
            self.wheels.set_wheels_speed(left, right)

    def _handle_waiting(self):
        if not has_to_wait_predetermined or self.outgoing_lane == AdjacentLane.east:
            self._transition_to_next()
            return

        now = time.time()
        per_check_interval = (
            merge_check_interval_s / (required_merge_confirmations - 1)
            if required_merge_confirmations > 1 else 0
        )
        if now - self.last_merge_check_time >= per_check_interval:
            self.last_merge_check_time = now
            detected_objects = self.object_detector.detect(self.frame) or []

            self.outgoing_lane = recheck_outgoing_lane(detected_objects, current_assumption=self.outgoing_lane)
            debug_print(f"Outgoing lane: {self.outgoing_lane}", debugging)

            can_merge = areEmptyLanesUntil(self.outgoing_lane, detected_objects)
            debug_print(f"Can merge: {can_merge}", debugging)

            self._update_merge_confirmation_counter(can_merge)
            debug_print(f"Confirmations: {self.merge_confirmation_counter}/{required_merge_confirmations}", debugging)

            if self.merge_confirmation_counter >= required_merge_confirmations:
                self._transition_to_next()

    def _handle_turning(self):
        left, right, reentered = self.turn_agent.compute_commands(self.frame)
        self.wheels.set_wheels_speed(left, right)

        if reentered:
            debug_print("Reentry detected, finishing.", debugging)
            self.wheels.set_wheels_speed(0.0, 0.0)
            self._transition_to_next()

    def _handle_finishing(self):
        left, right = self.convoy_agent.compute_commands(self.frame, self.lane_servoing_agent)
        self.wheels.set_wheels_speed(left, right)

    # ── State transitions ─────────────────────────────────────────────────────

    def _transition_to_next(self):
        self.state = get_next_state(self.state)
        if color_coded_leds:
            set_front_leds(self.leds, state_to_led_color[self.state])
        debug_print(get_state_entrance_console_message(self.state), debugging)
        self._enter_state()

    def _enter_state(self):
        {
            BotState.convoying: self._enter_convoying,
            BotState.waiting:   self._enter_waiting,
            BotState.turning:   self._enter_turning,
            BotState.finishing: lambda: None,
        }[self.state]()

    def _enter_convoying(self):
        self.waiting_for_red_line_to_disappear = False

    def _enter_waiting(self):
        self.merge_confirmation_counter = 0
        self.last_merge_check_time      = 0

    def _enter_turning(self):
        if use_pid_turn_agent:
            self.turn_agent = TurnAgentPID(self.outgoing_lane, self.wheels)
        else:
            self.turn_agent = TurnAgentOpenLoop(self.outgoing_lane)

    # ── Support ───────────────────────────────────────────────────────────────

    def _initialize_agents(self):
        self._initialize_lane_servoing_agent()
        self._initialize_convoy_agent()
        self._initialize_detector_if_necessary()

    def _initialize_lane_servoing_agent(self):
        self.lane_servoing_agent = LaneServoingAgent()
        register_live_agent(self.lane_servoing_agent)

    def _initialize_detector_if_necessary(self):
        needs_detector = _outgoing_lane_override is None or has_to_wait_predetermined
        if needs_detector:
            self.object_detector = ObjectDetector(
                config_path='config/object_detection_config.yaml',
                model_path='tasks/object_detection/models/best.onnx',
            )
            while not self.object_detector.model_loaded:
                time.sleep(1)
                debug_print("Waiting for model to load...", debugging)
            register_live_detector(self.object_detector)
            debug_print("Object detector loaded.", debugging)

    def _initialize_convoy_agent(self):
        self.convoy_agent = ConvoyAgentPID() if use_pid_convoy_agent else ConvoyAgentBinary()

    def _update_frame(self) -> bool:
        ok, frame_bgr = self.camera.read()
        if not ok:
            time.sleep(0.05)
            return False
        self.frame = FrameDictionary(frame_bgr)
        return True

    def _update_merge_confirmation_counter(self, can_merge):
        self.merge_confirmation_counter = self.merge_confirmation_counter + 1 if can_merge else 0

    def _drain_commands(self):
        if self.cmd_queue is None:
            return
        while not self.cmd_queue.empty():
            cmd = self.cmd_queue.get_nowait()
            key = cmd.get('key')

            if key == 'remove_objects':
                name_filter = str(cmd.get('value', '')).lower()
                if name_filter and hasattr(self.wheels, 'remove_objects'):
                    self.wheels.remove_objects(name_filter)
                    debug_print(f'[Agent] remove_objects: {name_filter}', debugging)

            elif key == 'manual_drive':
                self.manual_drive = cmd.get('value')
                if self.manual_drive is None and cmd.get('reset_to_convoy', False):
                    self.state = None
                    self._transition_to_next()  # → convoying, resets state-specific vars

    def _handle_manual(self):
        self.wheels.set_wheels_speed(self.manual_drive['left'], self.manual_drive['right'])
        self._update_debug(override_state='manual', detections=[])

    def _compute_debug_masks(self):
        self.red_mask    = get_red_mask(self.frame)
        mask_left, mask_right = detect_lane_markings(self.frame)
        self.yellow_mask = (mask_left  * 255).astype('uint8')
        self.white_mask  = (mask_right * 255).astype('uint8')

    def _update_debug(self, override_state=None, detections=None):
        if self.debug is None or self.debug_lock is None:
            return

        distance_measure = None
        try:
            distance_measure = calculate_distance_measure_to_leader(self.frame)
        except Exception:
            pass

        with self.debug_lock:
            self.debug.update(
                state=override_state or self.state.name,
                frame=self.frame.bgr.copy() if self.frame.bgr is not None else None,
                red_mask=self.red_mask,
                yellow_mask=self.yellow_mask,
                white_mask=self.white_mask,
                detections=detections if detections is not None else [],
                distance_measure=distance_measure,
                lane_debug=self.lane_servoing_agent.get_debug_info(),
            )