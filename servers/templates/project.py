from .base import render_template

_CONTENT = '''
    <div class="container">

        <!-- Left: debug grid only -->
        <div class="video-section" style="flex-direction:column;">
            <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;
                        letter-spacing:.05em;margin-bottom:6px;">Debug view</div>
            <img src="/debug_frame" class="stream" id="debugStream">
        </div>

        <!-- Right: controls sidebar -->
        <div class="controls-section">

            <!-- Status card -->
            <div class="card">
                <div class="card-header">
                    Status
                    <span id="statusDot" style="width:8px;height:8px;border-radius:50%;
                        background:var(--accent-green);display:inline-block;"></span>
                </div>
                <div id="statusTable" style="font-size:12px;">
                    <div style="color:var(--text-muted);text-align:center;padding:12px 0;">
                        Waiting for data...
                    </div>
                </div>
            </div>

            <!-- Manual drive card -->
            <div class="card">
                <div class="card-header">
                    Manual Drive
                    <span id="manualDot" style="width:8px;height:8px;border-radius:50%;
                        background:var(--text-muted);display:inline-block;"></span>
                </div>
                <div style="display:flex;flex-direction:column;gap:10px;">
                    <button class="button" id="manualToggleBtn" onclick="toggleManual()">Enable</button>
                    <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted);cursor:pointer;">
                        <input type="checkbox" id="resetToConvoyChk" style="cursor:pointer;">
                        Reset to convoy on exit
                    </label>
                    <div id="manualControls" style="display:none;flex-direction:column;gap:10px;">

                        <!-- Arrow key pad -->
                        <div style="display:grid;grid-template-columns:repeat(3,44px);
                                    grid-template-rows:repeat(3,44px);gap:4px;
                                    justify-content:center;">
                            <div></div>
                            <button class="arrow-btn" id="btn-up"    data-dir="up">&#x25B2;</button>
                            <div></div>
                            <button class="arrow-btn" id="btn-left"  data-dir="left">&#x25C4;</button>
                            <button class="arrow-btn" id="btn-stop"  data-dir="stop">&#x25A0;</button>
                            <button class="arrow-btn" id="btn-right" data-dir="right">&#x25BA;</button>
                            <div></div>
                            <button class="arrow-btn" id="btn-down"  data-dir="down">&#x25BC;</button>
                            <div></div>
                        </div>

                        <!-- Speed slider -->
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span style="font-size:11px;color:var(--text-muted);
                                         text-transform:uppercase;width:40px;flex-shrink:0;">Speed</span>
                            <input type="range" class="slider" id="driveSpeed"
                                   min="0.1" max="1" step="0.05" value="0.4" style="flex:1;">
                            <span id="driveSpeedLabel"
                                  style="width:34px;text-align:right;font-size:12px;
                                         font-family:monospace;color:var(--text-primary);">0.40</span>
                        </div>

                        <!-- Live wheel readout -->
                        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted);">
                            <span>L: <span id="readoutLeft"  style="color:var(--text-primary);font-family:monospace;">0.00</span></span>
                            <span style="font-size:10px;">Arrow keys work when enabled</span>
                            <span>R: <span id="readoutRight" style="color:var(--text-primary);font-family:monospace;">0.00</span></span>
                        </div>

                    </div>
                    <div id="manualStatus" class="status"></div>
                </div>
            </div>

            <!-- HSV bounds card (red detection) -->
            <div class="card">
                <div class="card-header">Red HSV Bounds</div>

                <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;">
                    Range 1 (hue 0-10)
                </div>
                <div id="hsv-lo1" style="margin-bottom:14px;">
                    <div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">Lower bound</div>
                    <div class="hsv-row" data-key="lo1" data-idx="0"></div>
                    <div class="hsv-row" data-key="lo1" data-idx="1"></div>
                    <div class="hsv-row" data-key="lo1" data-idx="2"></div>
                </div>
                <div id="hsv-hi1" style="margin-bottom:14px;">
                    <div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">Upper bound</div>
                    <div class="hsv-row" data-key="hi1" data-idx="0"></div>
                    <div class="hsv-row" data-key="hi1" data-idx="1"></div>
                    <div class="hsv-row" data-key="hi1" data-idx="2"></div>
                </div>

                <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;
                            border-top:1px solid var(--border-color);padding-top:10px;">
                    Range 2 (hue 170-180)
                </div>
                <div id="hsv-lo2" style="margin-bottom:14px;">
                    <div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">Lower bound</div>
                    <div class="hsv-row" data-key="lo2" data-idx="0"></div>
                    <div class="hsv-row" data-key="lo2" data-idx="1"></div>
                    <div class="hsv-row" data-key="lo2" data-idx="2"></div>
                </div>
                <div id="hsv-hi2" style="margin-bottom:10px;">
                    <div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">Upper bound</div>
                    <div class="hsv-row" data-key="hi2" data-idx="0"></div>
                    <div class="hsv-row" data-key="hi2" data-idx="1"></div>
                    <div class="hsv-row" data-key="hi2" data-idx="2"></div>
                </div>

                <button class="button" onclick="applyRedHsv()" style="margin-top:4px;">Apply</button>
                <div id="hsvStatus" class="status" style="margin-top:6px;"></div>
            </div>

            <!-- HSV bounds card (yellow + white lane detection) -->
            <div class="card">
                <div class="card-header">Lane HSV Bounds</div>

                <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;">
                    Yellow lane
                </div>
                <div style="margin-bottom:14px;">
                    <div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">Lower bound</div>
                    <div class="lane-hsv-row" data-lanekey="yellow_lower" data-idx="0"></div>
                    <div class="lane-hsv-row" data-lanekey="yellow_lower" data-idx="1"></div>
                    <div class="lane-hsv-row" data-lanekey="yellow_lower" data-idx="2"></div>
                </div>
                <div style="margin-bottom:14px;">
                    <div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">Upper bound</div>
                    <div class="lane-hsv-row" data-lanekey="yellow_upper" data-idx="0"></div>
                    <div class="lane-hsv-row" data-lanekey="yellow_upper" data-idx="1"></div>
                    <div class="lane-hsv-row" data-lanekey="yellow_upper" data-idx="2"></div>
                </div>

                <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;
                            border-top:1px solid var(--border-color);padding-top:10px;">
                    White lane
                </div>
                <div style="margin-bottom:14px;">
                    <div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">Lower bound</div>
                    <div class="lane-hsv-row" data-lanekey="white_lower" data-idx="0"></div>
                    <div class="lane-hsv-row" data-lanekey="white_lower" data-idx="1"></div>
                    <div class="lane-hsv-row" data-lanekey="white_lower" data-idx="2"></div>
                </div>
                <div style="margin-bottom:10px;">
                    <div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">Upper bound</div>
                    <div class="lane-hsv-row" data-lanekey="white_upper" data-idx="0"></div>
                    <div class="lane-hsv-row" data-lanekey="white_upper" data-idx="1"></div>
                    <div class="lane-hsv-row" data-lanekey="white_upper" data-idx="2"></div>
                </div>

                <button class="button" onclick="applyLaneHsv()" style="margin-top:4px;">Apply</button>
                <div id="laneHsvStatus" class="status" style="margin-top:6px;"></div>
            </div>

            <!-- Send command card -->
            <div class="card">
                <div class="card-header">Send Command</div>
                <div style="display:flex;flex-direction:column;gap:8px;">
                    <div style="display:flex;gap:6px;">
                        <input id="cmdKey" type="text" placeholder="key"
                            style="flex:1;padding:6px 8px;background:var(--bg-sidebar);
                                   border:1px solid var(--border-color);border-radius:4px;
                                   color:var(--text-primary);font-size:13px;">
                        <input id="cmdValue" type="text" placeholder="value"
                            style="flex:2;padding:6px 8px;background:var(--bg-sidebar);
                                   border:1px solid var(--border-color);border-radius:4px;
                                   color:var(--text-primary);font-size:13px;">
                    </div>
                    <button class="button" onclick="sendCommand()">Send</button>
                    <div id="cmdStatus" class="status"></div>
                </div>
            </div>
            <!-- Outgoing lane card -->
            <div class="card">
                <div class="card-header">Outgoing Lane</div>
                <div style="display:flex;flex-direction:column;gap:8px;">
                    <select id="outgoingLaneSelect" style="padding:6px 8px;background:var(--bg-sidebar);
                            border:1px solid var(--border-color);border-radius:4px;
                            color:var(--text-primary);font-size:13px;">
                        <option value="null">None (auto-detect)</option>
                        <option value="north">North</option>
                        <option value="east">East</option>
                        <option value="south">South</option>
                        <option value="west">West</option>
                    </select>
                    <button class="button" onclick="applyOutgoingLane()">Apply</button>
                    <div id="outgoingLaneStatus" class="status"></div>
                </div>
            </div>

        </div>
    </div>
'''

_EXTRA_CSS = '''
/* Status table rows */
#statusTable .row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid var(--border-color);
    align-items: baseline;
}
#statusTable .row:last-child { border-bottom: none; }
#statusTable .key  { color: var(--text-secondary); font-size: 12px; }
#statusTable .val  { color: var(--text-primary); font-weight: 500; font-size: 13px; font-family: monospace; }

/* State badge colour */
.state-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 600;
    font-family: monospace;
    text-transform: uppercase;
}
.state-convoying { background: rgba(31,111,235,.2); color: var(--accent-blue); }
.state-waiting   { background: rgba(210,153,34,.2); color: var(--accent-orange); }
.state-turning   { background: rgba(163,113,247,.2); color: var(--accent-purple); }
.state-finishing { background: rgba(63,185,80,.2);  color: var(--accent-green); }
.state-manual    { background: rgba(255,100,0,.2);  color: var(--accent-orange); }
.state-unknown   { background: rgba(110,118,129,.2); color: var(--text-muted); }

/* Arrow drive buttons */
.arrow-btn {
    width: 44px;
    height: 44px;
    background: var(--bg-sidebar);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    color: var(--text-primary);
    font-size: 16px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.1s, border-color 0.1s;
    user-select: none;
}
.arrow-btn:hover        { background: var(--bg-dark); border-color: var(--accent-blue); }
.arrow-btn.arrow-active { background: var(--accent-blue); border-color: var(--accent-blue); }
#btn-stop               { background: var(--bg-sidebar); color: var(--accent-red); }
#btn-stop:hover         { background: rgba(248,81,73,.15); border-color: var(--accent-red); }
#btn-stop.arrow-active  { background: var(--accent-red); color: white; }

/* HSV slider rows */
.hsv-row, .lane-hsv-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}
.hsv-label {
    width: 40px;
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    flex-shrink: 0;
}
'''

_EXTRA_JS = '''
/* ── Status polling ── */
function refreshStatus() {
    fetch('/status')
        .then(r => r.json())
        .then(data => {
            const table = document.getElementById('statusTable');
            const state = (data.state || 'unknown').toLowerCase();
            const badgeClass = 'state-' + state;
            let rows = `<div class="row">
                <span class="key">state</span>
                <span class="val"><span class="state-badge ${badgeClass}">${state}</span></span>
            </div>`;
            Object.keys(data).filter(k => k !== 'state').forEach(k => {
                rows += `<div class="row">
                    <span class="key">${k}</span>
                    <span class="val">${JSON.stringify(data[k])}</span>
                </div>`;
            });
            table.innerHTML = rows;
            document.getElementById('statusDot').style.background = 'var(--accent-green)';
        })
        .catch(() => {
            document.getElementById('statusDot').style.background = 'var(--accent-red)';
        });
}

/* ── Debug frame refresh ── */
function refreshDebugFrame() {
    const img = document.getElementById('debugStream');
    img.src = '/debug_frame?t=' + Date.now();
}

/* ── Red HSV sliders ── */
const HSV_MAX = { H: 180, S: 255, V: 255 };
const HSV_IDX_LABEL = ['H', 'S', 'V'];

const hsvState = { lo1: [0,120,100], hi1: [10,255,255], lo2: [170,120,100], hi2: [180,255,255] };

function buildHsvSliders() {
    document.querySelectorAll('.hsv-row').forEach(row => {
        const key = row.dataset.key;
        const idx = parseInt(row.dataset.idx);
        const ch  = HSV_IDX_LABEL[idx];
        const max = HSV_MAX[ch];
        const id  = `hsv-${key}-${idx}`;
        const val = hsvState[key][idx];
        row.innerHTML = `
            <span class="hsv-label">${ch}</span>
            <input type="range" class="slider" id="${id}"
                   min="0" max="${max}" value="${val}" style="flex:1;">
            <input type="number" class="input-box" id="${id}-input"
                   min="0" max="${max}" value="${val}" style="width:46px;">
        `;
        syncSliderInput(id, () => {
            hsvState[key][idx] = parseInt(document.getElementById(id).value);
        });
    });
}

function applyRedHsv() {
    postJSON('/hsv', { lo1: hsvState.lo1, hi1: hsvState.hi1, lo2: hsvState.lo2, hi2: hsvState.hi2 })
        .then(() => showStatus('hsvStatus', 'Applied', 'success'))
        .catch(e => showStatus('hsvStatus', 'Error: ' + e, 'error'));
}

function loadHsvBounds() {
    fetch('/hsv')
        .then(r => r.json())
        .then(data => {
            ['lo1','hi1','lo2','hi2'].forEach(k => {
                if (data[k]) {
                    hsvState[k] = data[k];
                    [0,1,2].forEach(i => setSliderValue(`hsv-${k}-${i}`, data[k][i]));
                }
            });
        });
}

/* ── Lane HSV sliders (yellow + white) ── */
const laneHsvState = {
    yellow_lower: [5,  80,  100],
    yellow_upper: [35, 192, 250],
    white_lower:  [0,  0,   180],
    white_upper:  [179, 80, 255],
};

function buildLaneHsvSliders() {
    document.querySelectorAll('.lane-hsv-row').forEach(row => {
        const key = row.dataset.lanekey;
        const idx = parseInt(row.dataset.idx);
        const ch  = HSV_IDX_LABEL[idx];
        const max = HSV_MAX[ch];
        const id  = `lane-${key}-${idx}`;
        const val = laneHsvState[key][idx];
        row.innerHTML = `
            <span class="hsv-label">${ch}</span>
            <input type="range" class="slider" id="${id}"
                   min="0" max="${max}" value="${val}" style="flex:1;">
            <input type="number" class="input-box" id="${id}-input"
                   min="0" max="${max}" value="${val}" style="width:46px;">
        `;
        syncSliderInput(id, () => {
            laneHsvState[key][idx] = parseInt(document.getElementById(id).value);
        });
    });
}

function applyLaneHsv() {
    postJSON('/hsv/lane', {
        yellow_lower: laneHsvState.yellow_lower,
        yellow_upper: laneHsvState.yellow_upper,
        white_lower:  laneHsvState.white_lower,
        white_upper:  laneHsvState.white_upper,
    })
        .then(() => showStatus('laneHsvStatus', 'Applied', 'success'))
        .catch(e => showStatus('laneHsvStatus', 'Error: ' + e, 'error'));
}

function loadLaneHsvBounds() {
    fetch('/hsv/lane')
        .then(r => r.json())
        .then(data => {
            ['yellow_lower','yellow_upper','white_lower','white_upper'].forEach(key => {
                ['h','s','v'].forEach((ch, i) => {
                    const val = data[`${key}_${ch}`];
                    if (val !== undefined) {
                        laneHsvState[key][i] = val;
                        setSliderValue(`lane-${key}-${i}`, val);
                    }
                });
            });
        });
}

/* ── Manual drive ── */
let manualEnabled = false;

// Maps direction name -> [left, right] wheel multipliers (applied to speed)
const DIR_VECTORS = {
    up:    [ 1,  1],
    down:  [-1, -1],
    left:  [-0.5,  0.5],
    right: [ 0.5, -0.5],
    stop:  [ 0,  0],
};

// Keys currently held down
const _keysHeld = new Set();

function _getSpeed() {
    return parseFloat(document.getElementById('driveSpeed').value);
}

function _sendWheels(left, right) {
    document.getElementById('readoutLeft').textContent  = left.toFixed(2);
    document.getElementById('readoutRight').textContent = right.toFixed(2);
    postJSON('/manual', {left, right}).catch(() => {});
}

function _driveDir(dir) {
    if (!manualEnabled) return;
    const speed = _getSpeed();
    const [lm, rm] = DIR_VECTORS[dir] || [0, 0];
    _sendWheels(lm * speed, rm * speed);
    // Highlight the button briefly
    const btn = document.getElementById('btn-' + dir);
    if (btn) {
        btn.classList.add('arrow-active');
        setTimeout(() => btn.classList.remove('arrow-active'), 150);
    }
}

function _applyHeldKeys() {
    if (!manualEnabled) return;
    // Priority: stop > up/down > left/right
    if (_keysHeld.has('stop'))  { _sendWheels(0, 0); return; }
    const speed = _getSpeed();
    let l = 0, r = 0;
    if (_keysHeld.has('up'))    { l += speed;  r += speed; }
    if (_keysHeld.has('down'))  { l -= speed;  r -= speed; }
    if (_keysHeld.has('left'))  { l -= speed * 0.5; r += speed * 0.5; }
    if (_keysHeld.has('right')) { l += speed * 0.5; r -= speed * 0.5; }
    l = Math.max(-1, Math.min(1, l));
    r = Math.max(-1, Math.min(1, r));
    _sendWheels(l, r);
}

function toggleManual() {
    manualEnabled = !manualEnabled;
    document.getElementById('manualToggleBtn').textContent = manualEnabled ? 'Disable' : 'Enable';
    document.getElementById('manualToggleBtn').style.background = manualEnabled ? 'var(--accent-red)' : '';
    document.getElementById('manualControls').style.display = manualEnabled ? 'flex' : 'none';
    document.getElementById('manualDot').style.background = manualEnabled ? 'var(--accent-green)' : 'var(--text-muted)';

    if (manualEnabled) {
        _sendWheels(0, 0);
    } else {
        _keysHeld.clear();
        document.getElementById('readoutLeft').textContent  = '0.00';
        document.getElementById('readoutRight').textContent = '0.00';
        const reset = document.getElementById('resetToConvoyChk').checked;
        postJSON('/manual', { reset_to_convoy: reset }).catch(() => {});
    }
}

// Speed slider label sync
document.getElementById('driveSpeed').addEventListener('input', function() {
    document.getElementById('driveSpeedLabel').textContent = parseFloat(this.value).toFixed(2);
    if (manualEnabled && _keysHeld.size > 0) _applyHeldKeys();
});

// On-screen arrow buttons (click = single nudge)
document.querySelectorAll('.arrow-btn').forEach(btn => {
    btn.addEventListener('click', () => _driveDir(btn.dataset.dir));
});

// Keyboard: held-key driving
const KEY_MAP = {
    ArrowUp:    'up',
    ArrowDown:  'down',
    ArrowLeft:  'left',
    ArrowRight: 'right',
    ' ':        'stop',   // spacebar = emergency stop
};

document.addEventListener('keydown', e => {
    const dir = KEY_MAP[e.key];
    if (!dir || !manualEnabled) return;
    e.preventDefault();
    if (_keysHeld.has(dir)) return;   // already held, don't re-send
    _keysHeld.add(dir);
    const btnEl = document.getElementById('btn-' + dir);
    if (btnEl) btnEl.classList.add('arrow-active');
    _applyHeldKeys();
});

document.addEventListener('keyup', e => {
    const dir = KEY_MAP[e.key];
    if (!dir) return;
    _keysHeld.delete(dir);
    const btnEl = document.getElementById('btn-' + dir);
    if (btnEl) btnEl.classList.remove('arrow-active');
    if (manualEnabled) {
        if (_keysHeld.size === 0) {
            _sendWheels(0, 0);   // coast to stop when all keys released
        } else {
            _applyHeldKeys();
        }
    }
});

/* ── Send command ── */
function sendCommand() {
    const key   = document.getElementById('cmdKey').value.trim();
    const value = document.getElementById('cmdValue').value.trim();
    if (!key) { showStatus('cmdStatus', 'Key cannot be empty', 'error'); return; }
    postJSON('/command', {key, value})
        .then(r => showStatus('cmdStatus', r.status === 'ok' ? 'Sent' : r.message,
                              r.status === 'ok' ? 'success' : 'error'))
        .catch(e => showStatus('cmdStatus', 'Error: ' + e, 'error'));
}

/* ── Outgoing lane ── */
function loadOutgoingLane() {
    fetch('/outgoing_lane')
        .then(r => r.json())
        .then(data => {
            document.getElementById('outgoingLaneSelect').value =
                data.outgoing_lane === null ? 'null' : data.outgoing_lane;
        });
}

function applyOutgoingLane() {
    const raw = document.getElementById('outgoingLaneSelect').value;
    const val = raw === 'null' ? null : raw;
    postJSON('/outgoing_lane', { outgoing_lane: val })
        .then(() => showStatus('outgoingLaneStatus', 'Applied', 'success'))
        .catch(e  => showStatus('outgoingLaneStatus', 'Error: ' + e, 'error'));
}

document.getElementById('cmdValue').addEventListener('keydown', e => {
    if (e.key === 'Enter') sendCommand();
});

/* ── Boot ── */
buildHsvSliders();
loadHsvBounds();
buildLaneHsvSliders();
loadLaneHsvBounds();
refreshStatus();
refreshDebugFrame();
setInterval(refreshStatus,     500);
setInterval(refreshDebugFrame, 100);
loadOutgoingLane();
'''


def get_template(title='Project', subtitle='Real Duckiebot'):
    return render_template(
        title=title,
        subtitle=subtitle,
        content_html=_CONTENT,
        extra_css=_EXTRA_CSS,
        extra_js=_EXTRA_JS,
    )