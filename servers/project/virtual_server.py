import sys
import os
import threading
import queue

script_dir   = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..', '..')
sys.path.insert(0, project_root)

import cv2
from flask import Flask, Response, render_template_string, jsonify, request
import numpy as np

from servers.templates.project import get_template as get_project_template
from tasks.project.packages import agent as project_agent
from tasks.project.packages.is_in_front_decider import get_hsv_bounds, set_hsv_bounds
import tasks.project.packages.detect_lane_markings as lane_markings_module

from duckiebot.camera_driver.godot_camera_driver import GodotCameraDriver, GodotCameraConfig
from duckiebot.wheel_driver.godot_wheels_driver import GodotWheelsDriver
from duckiebot.wheel_driver.wheels_driver_abs import WheelPWMConfiguration
from launcher.ports import find_available_port
from servers.common import make_frame_generator, shutdown_cleanup, suppress_http_logs


app        = Flask(__name__)
camera     = None
wheels     = None
running    = False
stop_event = threading.Event()

_debug      = {'state': 'unknown', 'frame': None, 'red_mask': None, 'detections': [],
               'yellow_mask': None, 'white_mask': None}
_debug_lock = threading.Lock()
_cmd_queue  = queue.SimpleQueue()


def _visualize(frame_rgb):
    """Main stream: raw camera frame with detection bboxes overlaid."""
    if frame_rgb is None:
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blank, 'Waiting for camera...', (140, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 2)
        return blank

    bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    out = bgr.copy()

    with _debug_lock:
        detections = list(_debug['detections'])
        state      = _debug['state']

    for det in detections:
        bbox, score, cls_id = det
        x1, y1, x2, y2 = bbox
        color = (0, 255, 0)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = {0: 'duckie', 1: 'truck', 2: 'sign'}.get(cls_id, str(cls_id))
        text = f"{label} {score:.2f}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(out, (x1, y1 - th - 5), (x1 + tw + 4, y1), color, -1)
        cv2.putText(out, text, (x1 + 2, y1 - 3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

    cv2.putText(out, state.upper(), (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    return out


generate_frames = make_frame_generator(lambda: camera, _visualize, quality=65)


def _build_debug_grid() -> np.ndarray:
    """
    Returns a 2×2 mosaic:
      [detections overlay  |  red mask + 75% line]
      [yellow mask         |  white mask          ]
    """
    with _debug_lock:
        frame      = _debug['frame']
        red_mask   = _debug['red_mask']
        yellow_mask= _debug['yellow_mask']
        white_mask = _debug['white_mask']
        detections = list(_debug['detections'])
        state      = _debug['state']

    H, W = 240, 320   # each cell size

    def _blank(label):
        img = np.zeros((H, W, 3), dtype=np.uint8)
        cv2.putText(img, label, (10, H // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 80, 80), 1)
        return img

    def _resize(img):
        return cv2.resize(img, (W, H))

    # ── Cell 0: detections overlay ──────────────────────────────────────────
    if frame is not None:
        bgr = frame if frame.shape[2] == 3 else cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        c0 = bgr.copy()
        for det in detections:
            bbox, score, cls_id = det
            x1, y1, x2, y2 = bbox
            cv2.rectangle(c0, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = {0: 'duckie', 1: 'truck', 2: 'sign'}.get(cls_id, str(cls_id))
            cv2.putText(c0, f"{label} {score:.2f}", (x1 + 2, max(y1 - 4, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        c0 = _resize(c0)
    else:
        c0 = _blank('detections')

    # ── Cell 1: red mask + 75% threshold line ───────────────────────────────
    if red_mask is not None:
        c1 = cv2.cvtColor(red_mask, cv2.COLOR_GRAY2BGR)
        # tint the active pixels red so it reads clearly
        c1[red_mask > 0] = (0, 0, 200)
        # draw the 75% line on the full-size mask, then resize
        line_y = int(red_mask.shape[0] * 0.75)
        cv2.line(c1, (0, line_y), (c1.shape[1], line_y), (0, 200, 255), 1)
        c1 = _resize(c1)
        cv2.putText(c1, '75%', (4, int(H * 0.75) - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 200, 255), 1)
    else:
        c1 = _blank('red mask')

    # ── Cell 2: yellow mask ──────────────────────────────────────────────────
    if yellow_mask is not None:
        c2 = cv2.cvtColor(yellow_mask, cv2.COLOR_GRAY2BGR)
        c2[yellow_mask > 0] = (0, 200, 200)   # yellow-ish tint
        c2 = _resize(c2)
    else:
        c2 = _blank('yellow mask')

    # ── Cell 3: white mask ───────────────────────────────────────────────────
    if white_mask is not None:
        c3 = cv2.cvtColor(white_mask, cv2.COLOR_GRAY2BGR)
        c3[white_mask > 0] = (220, 220, 220)
        c3 = _resize(c3)
    else:
        c3 = _blank('white mask')

    # ── Labels ───────────────────────────────────────────────────────────────
    for img, lbl in [(c0, 'Detections'), (c1, 'Red mask'), (c2, 'Yellow mask'), (c3, 'White mask')]:
        cv2.putText(img, lbl, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    top    = np.hstack([c0, c1])
    bottom = np.hstack([c2, c3])
    return np.vstack([top, bottom])


@app.route('/')
def index():
    html = get_project_template(title='Project', subtitle='Virtual Duckiebot')
    return render_template_string(html)


@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/debug_frame')
def debug_frame():
    grid = _build_debug_grid()
    _, jpeg = cv2.imencode('.jpg', grid, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return Response(jpeg.tobytes(), mimetype='image/jpeg')


@app.route('/status')
def status():
    with _debug_lock:
        debug_copy = dict(_debug)
    state = debug_copy.get('state', 'unknown')
    n_det = len(debug_copy.get('detections', []))
    resp = {'state': state, 'detections': n_det, 'running': running}
    # include distance_measure if computed by agent
    if 'distance_measure' in debug_copy:
        resp['distance'] = debug_copy.get('distance_measure')
    return jsonify(resp)


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


@app.route('/manual', methods=['POST'])
def manual():
    data = request.get_json(force=True) or {}
    # data is either {'left': float, 'right': float} to drive, or {} to disengage
    if 'left' in data and 'right' in data:
        _cmd_queue.put({'key': 'manual_drive', 'value': {'left': float(data['left']), 'right': float(data['right'])}})
    else:
        _cmd_queue.put({'key': 'manual_drive', 'value': None})
    return jsonify({'status': 'ok'})


@app.route('/command', methods=['POST'])
def command():
    data = request.json or {}
    key  = data.get('key')
    if not key:
        return jsonify({'status': 'error', 'message': 'missing key'}), 400
    _cmd_queue.put({'key': key, 'value': data.get('value', '')})
    return jsonify({'status': 'ok'})


def main():
    global camera, wheels, running

    import argparse
    ap = argparse.ArgumentParser(description='Project Server — Virtual')
    ap.add_argument('--port',        type=int, default=5000)
    ap.add_argument('--frame-port',  type=int, default=5001)
    ap.add_argument('--wheel-port',  type=int, default=5002)
    ap.add_argument('--godot-host',  type=str, default='localhost')
    args = ap.parse_args()

    suppress_http_logs()
    print('=' * 60)
    print('PROJECT SERVER — VIRTUAL')
    print('=' * 60)

    wheels = GodotWheelsDriver(
        WheelPWMConfiguration(),
        WheelPWMConfiguration(),
        godot_host=args.godot_host, godot_port=args.wheel_port,
    )

    camera = GodotCameraDriver(godot_config=GodotCameraConfig(host='0.0.0.0', port=args.frame_port))
    camera.start()

    stop_event.clear()
    try:
        threading.Thread(
            target=project_agent.main,
            args=(camera, wheels, None, stop_event, _debug, _debug_lock, _cmd_queue),
            daemon=True,
            name='ProjectAgent',
        ).start()
        print('  project.agent.main() running')
    except Exception as e:
        print(f'  Could not start project agent: {e}')

    running = True

    web_port = find_available_port(args.port)
    print(f'\nWeb Interface: http://localhost:{web_port}')
    print('=' * 60 + '\n')

    try:
        app.run(host='127.0.0.1', port=web_port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print('\nShutting down...')
    finally:
        shutdown_cleanup(wheels, camera, stop_event)


if __name__ == '__main__':
    sys.exit(main())