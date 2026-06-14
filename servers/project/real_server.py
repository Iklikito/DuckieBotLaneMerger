import sys
import os
import signal
import threading
import argparse
import time

script_dir   = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..', '..')
sys.path.insert(0, project_root)

from flask import Flask, Response, jsonify, request
import numpy as np
import cv2
import yaml as _yaml

from duckiebot.camera_driver import CameraDriver
from duckiebot.wheel_driver import DaguWheelsDriver
from duckiebot.wheel_driver.wheels_driver_abs import WheelPWMConfiguration
from duckiebot.led_driver import LEDDriver
from launcher.ports import find_available_port
from servers.common import make_frame_generator, shutdown_cleanup, suppress_http_logs
from servers.templates.project import get_template

import tasks.project.packages.agent as agent_module
from tasks.project.packages.is_in_front_decider import get_hsv_bounds, set_hsv_bounds
import tasks.project.packages.detect_lane_markings as lane_markings_module
from tasks.project.packages.ObjectDetector import ObjectDetector
from tasks.project.packages.TurnAgent import _get_config_path as get_turn_agent_config_path
from tasks.project.packages.settings import ROBOT_ID

app        = Flask(__name__)
camera     = None
wheels     = None
leds       = None
stop_event = threading.Event()

_debug = {'state': 'unknown', 'frame': None, 'red_mask': None, 'detections': [],
          'yellow_mask': None, 'white_mask': None, 'lane_debug': None}

_debug_lock = threading.Lock()
_cmd_queue  = __import__('queue').Queue()


def _visualize(frame):
    if frame is None:
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blank, "Waiting for camera...", (160, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 2)
        return blank
    return frame

def _draw_lane_servoing_overlay(img: np.ndarray, yellow_xs, white_xs, slice_ys) -> np.ndarray:
    H, W = img.shape[:2]
    sx = W / 640.0
    sy = H / 480.0

    # Draw horizontal slice lines
    for y in slice_ys:
        cv2.line(img, (0, int(y * sy)), (W, int(y * sy)), (60, 60, 60), 1)

    # Yellow points — matched per slice index
    for i, x in enumerate(yellow_xs):
        if i < len(slice_ys):
            cv2.circle(img, (int(x * sx), int(slice_ys[i] * sy)), 5, (0, 200, 200), -1)

    # White points
    for i, x in enumerate(white_xs):
        if i < len(slice_ys):
            cv2.circle(img, (int(x * sx), int(slice_ys[i] * sy)), 5, (220, 220, 220), -1)

    return img


generate_frames = make_frame_generator(lambda: camera, _visualize, quality=70, rgb=False)

HTML_TEMPLATE = get_template(title='Project', subtitle='Real Duckiebot')


@app.route('/')
def index():
    from flask import render_template_string
    return render_template_string(HTML_TEMPLATE)


@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def _build_debug_grid() -> np.ndarray:
    """2×2 mosaic: detections overlay | red mask+line / yellow mask | white mask."""
    with _debug_lock:
        frame       = _debug['frame']
        red_mask    = _debug['red_mask']
        yellow_mask = _debug['yellow_mask']
        white_mask  = _debug['white_mask']
        detections  = list(_debug['detections'])
        lane_debug  = _debug.get('lane_debug')

    H, W = 240, 320

    def _blank(label):
        img = np.zeros((H, W, 3), dtype=np.uint8)
        cv2.putText(img, label, (10, H // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 80, 80), 1)
        return img

    def _resize(img):
        return cv2.resize(img, (W, H))

    # Cell 0: detections overlay
    if frame is not None:
        c0 = frame.copy()
        for det in detections:
            bbox, score, cls_id = det
            x1, y1, x2, y2 = bbox
            cv2.rectangle(c0, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = {0: 'duckie', 1: 'truck', 2: 'sign'}.get(cls_id, str(cls_id))
            cv2.putText(c0, f"{label} {score:.2f}", (x1 + 2, max(y1 - 4, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        c0 = _resize(c0)
        if lane_debug:
            c0 = _draw_lane_servoing_overlay(
                c0,
                lane_debug.get('yellow_xs', []),
                lane_debug.get('white_xs',  []),
                lane_debug.get('slice_ys',  []),
            )
    else:
        c0 = _blank('detections')

    # Cell 1: red mask + 75% line
    if red_mask is not None:
        c1 = cv2.cvtColor(red_mask, cv2.COLOR_GRAY2BGR)
        c1[red_mask > 0] = (0, 0, 200)
        line_y = int(red_mask.shape[0] * 0.75)
        cv2.line(c1, (0, line_y), (c1.shape[1], line_y), (0, 200, 255), 1)
        c1 = _resize(c1)
        cv2.putText(c1, '75%', (4, int(H * 0.75) - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 200, 255), 1)
    else:
        c1 = _blank('red mask')

    # Cell 2: yellow mask
    if yellow_mask is not None:
        c2 = cv2.cvtColor(yellow_mask, cv2.COLOR_GRAY2BGR)
        c2[yellow_mask > 0] = (0, 200, 200)
        c2 = _resize(c2)
    else:
        c2 = _blank('yellow mask')

    # Cell 3: white mask
    if white_mask is not None:
        c3 = cv2.cvtColor(white_mask, cv2.COLOR_GRAY2BGR)
        c3[white_mask > 0] = (220, 220, 220)
        c3 = _resize(c3)
    else:
        c3 = _blank('white mask')

    for img, lbl in [(c0, 'Detections'), (c1, 'Red mask'), (c2, 'Yellow mask'), (c3, 'White mask')]:
        cv2.putText(img, lbl, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    return np.vstack([np.hstack([c0, c1]), np.hstack([c2, c3])])


def _make_debug_generator():
    def generate():
        while True:
            try:
                grid = _build_debug_grid()
                _, jpeg = cv2.imencode('.jpg', grid, [cv2.IMWRITE_JPEG_QUALITY, 70])
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + jpeg.tobytes() + b'\r\n')
                time.sleep(0.033)
            except Exception as e:
                print(f'[DebugStream] Error: {e}')
                time.sleep(0.05)
    return generate

generate_debug_frames = _make_debug_generator()

@app.route('/debug_stream')
def debug_stream():
    return Response(generate_debug_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/debug_frame')
def debug_frame():
    grid = _build_debug_grid()
    _, jpeg = cv2.imencode('.jpg', grid, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return Response(jpeg.tobytes(), mimetype='image/jpeg')


@app.route('/status')
def status():
    with _debug_lock:
        state = _debug['state']
        n_det = len(_debug['detections'])
    return jsonify({'state': state, 'detections': n_det})


@app.route('/hsv', methods=['GET'])
def hsv_get():
    return jsonify(get_hsv_bounds())


@app.route('/hsv', methods=['POST'])
def hsv_post():
    data = request.get_json(force=True)
    set_hsv_bounds(
        lo1=data.get('lo1'),
        hi1=data.get('hi1'),
        lo2=data.get('lo2'),
        hi2=data.get('hi2'),
    )
    return jsonify({'status': 'ok', **get_hsv_bounds()})


@app.route('/hsv/lane', methods=['GET'])
def hsv_lane_get():
    return jsonify(lane_markings_module.get_hsv_bounds())


@app.route('/hsv/lane', methods=['POST'])
def hsv_lane_post():
    data = request.get_json(force=True)
    lane_markings_module.set_hsv_bounds(
        yellow_lower=data.get('yellow_lower'),
        yellow_upper=data.get('yellow_upper'),
        white_lower=data.get('white_lower'),
        white_upper=data.get('white_upper'),
    )
    return jsonify({'status': 'ok', **lane_markings_module.get_hsv_bounds()})


@app.route('/turn_config', methods=['GET'])
def turn_config_get():
    with open(get_turn_agent_config_path(ROBOT_ID)) as f:
        return jsonify(_yaml.safe_load(f))

@app.route('/turn_config', methods=['POST'])
def turn_config_post():
    data = request.get_json(force=True) or {}
    path = get_turn_agent_config_path(ROBOT_ID)
    with open(path) as f:
        cfg = _yaml.safe_load(f)
    direction = data.get('direction')
    if direction not in cfg:
        return jsonify({'status': 'error', 'message': f'unknown direction: {direction}'}), 400
    cfg[direction]['turn']            = str(data['turn'])
    cfg[direction]['turn_speed']      = float(data['turn_speed'])
    cfg[direction]['turn_bias']       = float(data['turn_bias'])
    cfg[direction]['reentry_delay_s'] = float(data['reentry_delay_s'])
    with open(path, 'w') as f:
        _yaml.dump(cfg, f, default_flow_style=False)
    return jsonify({'status': 'ok', **cfg})


@app.route('/outgoing_lane', methods=['GET'])
def outgoing_lane_get():
    return jsonify({'outgoing_lane': agent_module.get_outgoing_lane()})

@app.route('/outgoing_lane', methods=['POST'])
def outgoing_lane_post():
    data = request.get_json(force=True) or {}
    val  = data.get('outgoing_lane')   # 'north'/'east'/'south'/'west' or null
    agent_module.set_outgoing_lane(val)
    return jsonify({'status': 'ok'})


@app.route('/manual', methods=['POST'])
def manual():
    data = request.get_json(force=True) or {}
    if 'left' in data and 'right' in data:
        _cmd_queue.put({'key': 'manual_drive', 'value': {'left': float(data['left']), 'right': float(data['right'])}})
    else:
        reset = bool(data.get('reset_to_convoy', False))
        _cmd_queue.put({'key': 'manual_drive', 'value': None, 'reset_to_convoy': reset})
    return jsonify({'status': 'ok'})


@app.route('/command', methods=['POST'])
def command():
    data = request.get_json(force=True) or {}
    key  = data.get('key')
    if not key:
        return jsonify({'status': 'error', 'message': 'missing key'}), 400
    _cmd_queue.put({'key': key, 'value': data.get('value', '')})
    return jsonify({'status': 'ok'})


@app.route('/shutdown')
def shutdown():
    shutdown_cleanup(wheels, camera, stop_event)
    return jsonify({'status': 'ok'})


def main():
    global camera, wheels, leds, stop_event

    ap = argparse.ArgumentParser(description='Project Server — Real Hardware')
    ap.add_argument('--port', type=int, default=5000)
    args = ap.parse_args()

    suppress_http_logs()
    print('=' * 60)
    print('PROJECT SERVER — REAL HARDWARE')
    print('=' * 60)

    print('\n[1/4] Initializing LED driver...')
    try:
        leds = LEDDriver()
        leds.all_off()
        print('  LEDs: ok')
    except Exception as e:
        print(f'  LEDs: not available ({e})')
        leds = None

    print('\n[2/4] Initializing wheels driver...')
    wheels = DaguWheelsDriver(WheelPWMConfiguration(), WheelPWMConfiguration())
    print('  Wheels: ok')

    print('\n[3/4] Initializing camera driver...')
    camera = CameraDriver()
    camera.start()
    print('  Camera: ok')

    print('\n[4/4] Starting agent...')
    stop_event.clear()
    threading.Thread(
        target=agent_module.main,
        args=(camera, wheels, leds, stop_event, _debug, _debug_lock, _cmd_queue),
        daemon=True,
        name='AgentThread',
    ).start()
    print('  agent.main() running')

    def _shutdown(signum, frame):
        print('\nShutting down...')
        if leds:
            try:
                leds.all_off()
                leds.release()
            except Exception:
                pass
        shutdown_cleanup(wheels, camera, stop_event)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT,  _shutdown)

    web_port = find_available_port(args.port)
    print(f'\nWeb interface: http://localhost:{web_port}/')
    print('Press Ctrl+C to stop\n')

    try:
        app.run(host='0.0.0.0', port=web_port, debug=False, threaded=True)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if leds:
            try:
                leds.all_off()
                leds.release()
            except Exception:
                pass
        shutdown_cleanup(wheels, camera, stop_event)


if __name__ == '__main__':
    sys.exit(main())