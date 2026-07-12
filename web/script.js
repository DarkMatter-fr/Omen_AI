/* ==========================================
   OMEN OS — JAVASCRIPT BRIDGE (script.js)
   v4.0 — Milestone 4: Modern Chat UI
   ========================================== */

'use strict';

// ─── State ────────────────────────────────────────────────────────────────────

let _currentState   = 'idle';       // 'idle' | 'listening' | 'thinking'
let _thinkingBubble = null;         // DOM node for the animated thinking indicator
let _audioCtx       = null;         // Web Audio API context
let _analyser       = null;         // AnalyserNode for mic visualisation
let _micStream      = null;         // MediaStream from getUserMedia
let _rafId          = null;         // requestAnimationFrame ID
let _welcomeRemoved = false;        // track if welcome card was cleared

// ─── Canvas Setup ─────────────────────────────────────────────────────────────

const canvas = document.getElementById('waveform-canvas');
const ctx2d  = canvas ? canvas.getContext('2d') : null;

/** Resize canvas to match its CSS display size (handles DPR for sharp rendering). */
function resizeCanvas() {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const dpr  = window.devicePixelRatio || 1;
    canvas.width  = rect.width  * dpr;
    canvas.height = rect.height * dpr;
    if (ctx2d) ctx2d.scale(dpr, dpr);
}

window.addEventListener('resize', () => { resizeCanvas(); });

// ─── Canvas Waveform Animator ─────────────────────────────────────────────────

/**
 * Main canvas draw loop.
 * Dispatches to the correct render function based on current state.
 */
function animateCanvas() {
    _rafId = requestAnimationFrame(animateCanvas);

    if (!ctx2d || !canvas) return;

    const W = canvas.width  / (window.devicePixelRatio || 1);
    const H = canvas.height / (window.devicePixelRatio || 1);
    const cx = W / 2;
    const cy = H / 2;
    const now = performance.now() / 1000; // seconds

    // Clear
    ctx2d.clearRect(0, 0, W, H);

    if (_currentState === 'idle')      renderIdle(ctx2d, W, H, cx, cy, now);
    if (_currentState === 'listening') renderListening(ctx2d, W, H, cx, cy, now);
    if (_currentState === 'thinking')  renderThinking(ctx2d, W, H, cx, cy, now);
}

/**
 * IDLE — slow ambient plasma orb matching the reference image.
 * Deep void core, layered amber/gold radial gradients, multiple
 * concentric rings, particle wisps rotating at different speeds.
 */
function renderIdle(c, W, H, cx, cy, t) {
    const baseR = Math.min(W, H) * 0.36;
    const pulse = 1 + Math.sin(t * 0.9) * 0.028;
    const R     = baseR * pulse;

    // ── Outer ambient haze (very faint, wide) ──
    const haze = c.createRadialGradient(cx, cy, R * 0.2, cx, cy, R * 2.1);
    haze.addColorStop(0,   'rgba(200, 80, 0, 0.09)');
    haze.addColorStop(0.4, 'rgba(150, 50, 0, 0.04)');
    haze.addColorStop(1,   'rgba(0, 0, 0, 0)');
    c.fillStyle = haze;
    c.fillRect(0, 0, W, H);

    // ── Mid glow ring ──
    const midGlow = c.createRadialGradient(cx, cy, R * 0.5, cx, cy, R * 1.3);
    midGlow.addColorStop(0,   'rgba(255, 110, 0, 0.12)');
    midGlow.addColorStop(0.5, 'rgba(200, 60, 0, 0.05)');
    midGlow.addColorStop(1,   'rgba(0, 0, 0, 0)');
    c.beginPath();
    c.arc(cx, cy, R * 1.3, 0, Math.PI * 2);
    c.fillStyle = midGlow;
    c.fill();

    // ── Plasma core — white-gold to deep amber ──
    const core = c.createRadialGradient(cx, cy, 0, cx, cy, R);
    core.addColorStop(0,    'rgba(255, 245, 180, 0.98)'); // blinding white-gold
    core.addColorStop(0.08, 'rgba(255, 220, 80,  0.92)');
    core.addColorStop(0.20, 'rgba(255, 160, 20,  0.80)');
    core.addColorStop(0.40, 'rgba(255, 100, 0,   0.55)');
    core.addColorStop(0.60, 'rgba(200, 55,  0,   0.28)');
    core.addColorStop(0.80, 'rgba(100, 20,  0,   0.10)');
    core.addColorStop(1,    'rgba(0, 0, 0, 0)');
    c.beginPath();
    c.arc(cx, cy, R, 0, Math.PI * 2);
    c.fillStyle = core;
    c.fill();

    // ── Concentric orbit rings at varying opacities ──
    drawRing(c, cx, cy, R * 0.45, 'rgba(255, 220, 80, 0.28)', 0.8, t * 0.05);
    drawDashedRing(c, cx, cy, R * 0.62, 'rgba(255, 180, 40, 0.20)', 0.8, 20, t * 0.12);
    drawRing(c, cx, cy, R * 0.78, 'rgba(255, 150, 0,  0.16)', 1.0, t * 0.07);
    drawDashedRing(c, cx, cy, R * 0.93, 'rgba(255, 120, 0,  0.14)', 0.8, 28, -t * 0.09);
    drawRing(c, cx, cy, R * 1.10, 'rgba(255, 90,  0,  0.07)', 0.8);
    drawDashedRing(c, cx, cy, R * 1.22, 'rgba(200, 70,  0,  0.06)', 0.6, 36, t * 0.04);

    // ── Plasma energy wisps (the 'crackle' lines from the reference) ──
    const wispCount = 8;
    for (let i = 0; i < wispCount; i++) {
        const phase   = (i / wispCount) * Math.PI * 2;
        const speed   = 0.15 + (i % 3) * 0.07;
        const angle   = phase + t * speed;
        const rInner  = R * (0.18 + (i % 4) * 0.08);
        const rOuter  = R * (0.55 + Math.sin(t * 0.7 + i) * 0.12);
        const arcLen  = 0.25 + Math.sin(t * 1.2 + i * 0.9) * 0.12;
        const alpha   = 0.10 + Math.sin(t * 1.5 + i) * 0.06;
        c.beginPath();
        c.moveTo(cx + Math.cos(angle) * rInner, cy + Math.sin(angle) * rInner);
        c.lineTo(cx + Math.cos(angle) * rOuter, cy + Math.sin(angle) * rOuter);
        c.strokeStyle = `rgba(255, ${140 + i * 10}, 20, ${alpha})`;
        c.lineWidth   = 0.6;
        c.stroke();
        // Arc along the wisp end
        c.beginPath();
        c.arc(cx, cy, rOuter, angle - arcLen * 0.5, angle + arcLen * 0.5);
        c.strokeStyle = `rgba(255, ${130 + i * 8}, 10, ${alpha * 0.8})`;
        c.lineWidth   = 0.5;
        c.stroke();
    }

    // ── Slow outer spiral arcs ──
    for (let i = 0; i < 4; i++) {
        const base  = t * 0.18 + (i * Math.PI / 2);
        const len   = Math.PI * 0.55 + Math.sin(t * 0.6 + i) * 0.1;
        const rArc  = R * (0.70 + i * 0.06);
        c.beginPath();
        c.arc(cx, cy, rArc, base, base + len);
        c.strokeStyle = `rgba(255, ${100 + i * 18}, 0, ${0.09 + i * 0.02})`;
        c.lineWidth   = 0.8;
        c.stroke();
    }
}

/**
 * LISTENING — audio-reactive circular equaliser + pulsing red-tinted core.
 */
function renderListening(c, W, H, cx, cy, t) {
    const baseR = Math.min(W, H) * 0.36;
    const pulse = 1 + Math.sin(t * 4) * 0.018;
    const R     = baseR * pulse;
    const bars  = 80;

    // ── Outer listening aura ──
    const aura = c.createRadialGradient(cx, cy, R * 0.5, cx, cy, R * 1.8);
    aura.addColorStop(0,   'rgba(255, 40, 40, 0.10)');
    aura.addColorStop(0.5, 'rgba(200, 20, 30, 0.04)');
    aura.addColorStop(1,   'rgba(0, 0, 0, 0)');
    c.fillStyle = aura;
    c.fillRect(0, 0, W, H);

    // ── Core — red/orange tinted ──
    const core = c.createRadialGradient(cx, cy, 0, cx, cy, R);
    core.addColorStop(0,    'rgba(255, 220, 160, 0.92)');
    core.addColorStop(0.12, 'rgba(255, 120,  60, 0.80)');
    core.addColorStop(0.30, 'rgba(240,  40,  40, 0.50)');
    core.addColorStop(0.55, 'rgba(180,  15,  15, 0.25)');
    core.addColorStop(1,    'rgba(0, 0, 0, 0)');
    c.beginPath();
    c.arc(cx, cy, R, 0, Math.PI * 2);
    c.fillStyle = core;
    c.fill();

    // ── Get FFT data (or fallback) ──
    let dataArray = new Uint8Array(bars);
    if (_analyser) {
        _analyser.getByteFrequencyData(dataArray);
    } else {
        for (let i = 0; i < bars; i++) {
            dataArray[i] = 60 + Math.sin(t * 4 + i * 0.35) * 80 + Math.sin(t * 7 + i * 0.18) * 40;
        }
    }

    // ── Circular equaliser bars (outer ring) ──
    const barR    = R * 1.06;
    const maxBarH = R * 0.50;
    for (let i = 0; i < bars; i++) {
        const angle  = (i / bars) * Math.PI * 2 - Math.PI / 2;
        const norm   = Math.max(0, Math.min(1, dataArray[i] / 255));
        const barH   = norm * maxBarH + 1.5;
        const x1     = cx + Math.cos(angle) * barR;
        const y1     = cy + Math.sin(angle) * barR;
        const x2     = cx + Math.cos(angle) * (barR + barH);
        const y2     = cy + Math.sin(angle) * (barR + barH);
        const alpha  = 0.3 + norm * 0.65;
        const green  = Math.round(50 + norm * 80);
        c.beginPath();
        c.moveTo(x1, y1);
        c.lineTo(x2, y2);
        c.strokeStyle = `rgba(255, ${green}, 40, ${alpha})`;
        c.lineWidth   = 1.8;
        c.stroke();
    }

    // ── Inner orbit ring ──
    drawRing(c, cx, cy, R * 0.88, 'rgba(255, 60, 60, 0.35)', 1.2);
    drawDashedRing(c, cx, cy, R * 0.55, 'rgba(255, 80, 50, 0.28)', 0.8, 16, t * 0.3);
}

/**
 * THINKING — fast-spinning multi-orbit arcs, fractalized energy pattern.
 */
function renderThinking(c, W, H, cx, cy, t) {
    const baseR = Math.min(W, H) * 0.36;
    const pulse = 1 + Math.sin(t * 3.5) * 0.022;
    const R     = baseR * pulse;

    // ── Outer energy corona ──
    const corona = c.createRadialGradient(cx, cy, R * 0.4, cx, cy, R * 1.6);
    corona.addColorStop(0,   'rgba(255, 180, 0, 0.14)');
    corona.addColorStop(0.5, 'rgba(200, 100, 0, 0.05)');
    corona.addColorStop(1,   'rgba(0, 0, 0, 0)');
    c.fillStyle = corona;
    c.fillRect(0, 0, W, H);

    // ── Bright thinking core ──
    const core = c.createRadialGradient(cx, cy, 0, cx, cy, R);
    core.addColorStop(0,    'rgba(255, 255, 200, 0.98)');
    core.addColorStop(0.10, 'rgba(255, 230, 80,  0.90)');
    core.addColorStop(0.25, 'rgba(255, 180, 20,  0.72)');
    core.addColorStop(0.45, 'rgba(255, 120, 0,   0.48)');
    core.addColorStop(0.68, 'rgba(180, 55,  0,   0.22)');
    core.addColorStop(1,    'rgba(0, 0, 0, 0)');
    c.beginPath();
    c.arc(cx, cy, R, 0, Math.PI * 2);
    c.fillStyle = core;
    c.fill();

    // ── Multi-speed spinning arc layers ──
    const layers = [
        { r: R * 0.48, speed:  2.8,  len: 1.4,  color: 'rgba(255, 240, 100, 0.60)', w: 1.5 },
        { r: R * 0.62, speed: -2.0,  len: 0.9,  color: 'rgba(255, 200,  50, 0.45)', w: 1.2 },
        { r: R * 0.76, speed:  3.5,  len: 0.65, color: 'rgba(255, 160,  10, 0.38)', w: 1.0 },
        { r: R * 0.90, speed: -1.5,  len: 1.2,  color: 'rgba(255, 120,   0, 0.28)', w: 0.8 },
        { r: R * 1.06, speed:  4.2,  len: 0.45, color: 'rgba(220,  80,   0, 0.20)', w: 0.7 },
        { r: R * 1.20, speed: -3.0,  len: 0.80, color: 'rgba(180,  50,   0, 0.15)', w: 0.6 },
    ];

    for (const arc of layers) {
        const start = t * arc.speed;
        c.beginPath();
        c.arc(cx, cy, arc.r, start, start + arc.len);
        c.strokeStyle = arc.color;
        c.lineWidth   = arc.w;
        c.stroke();
        // Counter arc (ghost echo)
        c.beginPath();
        c.arc(cx, cy, arc.r, start + Math.PI * 0.8, start + Math.PI * 0.8 + arc.len * 0.5);
        c.strokeStyle = arc.color.replace(/[\d.]+\)$/, '0.12)');
        c.lineWidth   = arc.w * 0.5;
        c.stroke();
    }

    // ── Radial energy spike lines ──
    const spikes = 12;
    for (let i = 0; i < spikes; i++) {
        const angle  = (i / spikes) * Math.PI * 2 + t * 1.2;
        const rIn    = R * 0.22;
        const rOut   = R * (0.38 + Math.sin(t * 3 + i * 0.7) * 0.08);
        const alpha  = 0.10 + Math.sin(t * 2 + i) * 0.06;
        c.beginPath();
        c.moveTo(cx + Math.cos(angle) * rIn, cy + Math.sin(angle) * rIn);
        c.lineTo(cx + Math.cos(angle) * rOut, cy + Math.sin(angle) * rOut);
        c.strokeStyle = `rgba(255, 220, 60, ${alpha})`;
        c.lineWidth   = 0.7;
        c.stroke();
    }

    // ── Inner dashed pulse rings ──
    drawDashedRing(c, cx, cy, R * 0.35, 'rgba(255, 240, 100, 0.35)', 0.8, 14, t * 0.8);
    drawDashedRing(c, cx, cy, R * 0.55, 'rgba(255, 200,  60, 0.22)', 0.7, 20, -t * 0.6);
}

/** Draw a solid circle ring. */
function drawRing(c, cx, cy, r, color, lw = 1, rotOffset = 0) {
    c.beginPath();
    c.arc(cx, cy, r, rotOffset, Math.PI * 2 + rotOffset);
    c.strokeStyle = color;
    c.lineWidth   = lw;
    c.stroke();
}

/** Draw a dashed circle ring (rotating). */
function drawDashedRing(c, cx, cy, r, color, lw, segments, rotOffset = 0) {
    const segAngle = (Math.PI * 2) / segments;
    const gap      = segAngle * 0.32;
    for (let i = 0; i < segments; i++) {
        const start = rotOffset + i * segAngle;
        const end   = start + segAngle - gap;
        c.beginPath();
        c.arc(cx, cy, r, start, end);
        c.strokeStyle = color;
        c.lineWidth   = lw;
        c.stroke();
    }
}

// ─── Assistant State Engine ────────────────────────────────────────────────────

/**
 * Python calls this to update the orb and UI state.
 * @param {string} state — 'idle' | 'listening' | 'thinking'
 */
eel.expose(setAssistantState);
function setAssistantState(state) {
    _currentState = state;

    // Update the CSS ring overlay
    const ring = document.getElementById('visualizer-ring');
    if (ring) ring.className = `vis-ring ${state}`;

    // Update the orb state label
    const orbLabel = document.getElementById('orb-state-label');
    if (orbLabel) {
        const labels = { idle: 'IDLE', listening: 'LISTENING', thinking: 'PROCESSING' };
        orbLabel.textContent = labels[state] || state.toUpperCase();
    }

    // Update the chat status badge
    const badge = document.getElementById('chat-status-badge');
    if (badge) {
        badge.className = 'chat-status-badge';
        if (state === 'listening') { badge.classList.add('badge-listening'); badge.textContent = 'LISTENING'; }
        else if (state === 'thinking') { badge.classList.add('badge-thinking'); badge.textContent = 'PROCESSING'; }
        else { badge.textContent = 'STANDBY'; }
    }

    // Mic button visual state
    const micBtn = document.getElementById('mic-btn');
    if (micBtn) {
        micBtn.disabled = (state === 'listening' || state === 'thinking');
        if (state === 'listening') micBtn.classList.add('mic-active');
        else micBtn.classList.remove('mic-active');
    }

    // Manage microphone Web Audio stream
    if (state === 'listening') {
        _startMicCapture();
    } else {
        _stopMicCapture();
        // Remove thinking indicator bubble when done
        if (state === 'idle' && _thinkingBubble) {
            _thinkingBubble.remove();
            _thinkingBubble = null;
        }
    }

    // Show thinking bubble
    if (state === 'thinking' && !_thinkingBubble) {
        _thinkingBubble = _createThinkingBubble();
    }
}

// ─── Mic Web Audio Capture ────────────────────────────────────────────────────

async function _startMicCapture() {
    try {
        if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        _micStream  = await navigator.mediaDevices.getUserMedia({ audio: true });
        const src   = _audioCtx.createMediaStreamSource(_micStream);
        _analyser   = _audioCtx.createAnalyser();
        _analyser.fftSize = 128;
        src.connect(_analyser);
    } catch (e) {
        // Microphone access denied — waveform falls back to animated sine
        _analyser = null;
    }
}

function _stopMicCapture() {
    if (_micStream) {
        _micStream.getTracks().forEach(t => t.stop());
        _micStream = null;
    }
    _analyser = null;
}

// ─── Chat Bubble Functions ────────────────────────────────────────────────────

/**
 * Appends a chat bubble for the given actor.
 * Called from Python via eel.appendChatBubble() or directly by JS.
 * @param {string} actor — 'user' | 'omen'
 * @param {string} message — text content
 * @param {boolean} stream — if true, uses streaming typewriter effect
 */
eel.expose(appendChatBubble);
function appendChatBubble(actor, message, stream = false) {
    const chatWindow = document.getElementById('chat-window');
    if (!chatWindow) return;

    // Remove welcome card on first real message
    if (!_welcomeRemoved) {
        const welcome = chatWindow.querySelector('.chat-welcome');
        if (welcome) { welcome.remove(); _welcomeRemoved = true; }
    }

    const msgClass    = actor === 'user' ? 'msg-user' : 'msg-omen';
    const actorLabel  = actor === 'user' ? 'YOU' : 'F.R.I.D.A.Y.';

    const wrapper = document.createElement('div');
    wrapper.className = `chat-message ${msgClass}`;

    const actorEl = document.createElement('div');
    actorEl.className = 'bubble-actor';
    actorEl.textContent = actorLabel;

    const body = document.createElement('div');
    body.className = 'bubble-body';

    wrapper.appendChild(actorEl);
    wrapper.appendChild(body);
    chatWindow.appendChild(wrapper);

    // Scroll to bottom
    chatWindow.scrollTop = chatWindow.scrollHeight;

    if (stream && actor === 'omen') {
        streamText(body, message);
    } else {
        body.textContent = message;
    }

    return wrapper;
}

/**
 * Types text character by character into a DOM element.
 * @param {HTMLElement} el — target element
 * @param {string} text — full text to type
 * @param {number} speed — ms per character (default 18)
 */
function streamText(el, text, speed = 18) {
    return new Promise(resolve => {
        // Add blinking cursor
        const cursor = document.createElement('span');
        cursor.className = 'typing-cursor';
        el.appendChild(cursor);

        let i = 0;
        const chatWindow = document.getElementById('chat-window');

        function typeNext() {
            if (i < text.length) {
                // Insert character before cursor
                const charNode = document.createTextNode(text[i]);
                el.insertBefore(charNode, cursor);
                i++;
                if (chatWindow) chatWindow.scrollTop = chatWindow.scrollHeight;
                setTimeout(typeNext, speed);
            } else {
                // Remove cursor when done
                cursor.remove();
                resolve();
            }
        }
        typeNext();
    });
}

/**
 * Creates and appends the animated "thinking" bubble (3 dots).
 */
function _createThinkingBubble() {
    const chatWindow = document.getElementById('chat-window');
    if (!chatWindow) return null;

    if (!_welcomeRemoved) {
        const welcome = chatWindow.querySelector('.chat-welcome');
        if (welcome) { welcome.remove(); _welcomeRemoved = true; }
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'chat-message msg-omen';

    const actorEl = document.createElement('div');
    actorEl.className = 'bubble-actor';
    actorEl.textContent = 'F.R.I.D.A.Y.';

    const body = document.createElement('div');
    body.className = 'bubble-body bubble-thinking';

    for (let i = 0; i < 3; i++) {
        const dot = document.createElement('span');
        dot.className = 'think-dot';
        body.appendChild(dot);
    }

    wrapper.appendChild(actorEl);
    wrapper.appendChild(body);
    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop = chatWindow.scrollHeight;

    return wrapper;
}

// ─── Holographic Terminal Logger ──────────────────────────────────────────────

/**
 * Python calls this to print system status to the terminal strip.
 * @param {string} message
 */
eel.expose(logToTerminal);
function logToTerminal(message) {
    const terminal = document.getElementById('terminal-log');
    if (!terminal) return;

    const entry   = document.createElement('p');
    const prefix  = document.createElement('span');
    prefix.className = 'log-prefix';
    prefix.textContent = '> ';

    const content = document.createElement('span');
    const msgStr  = String(message);

    if (msgStr.startsWith('YOU:'))                              entry.classList.add('log-user');
    else if (msgStr.startsWith('F.R.I.D.A.Y:'))                entry.classList.add('log-friday');
    else if (msgStr.startsWith('ERROR:'))                       entry.classList.add('log-error');
    else if (msgStr.startsWith('ACTION:') || msgStr.startsWith('STATUS:')) entry.classList.add('log-system');

    content.textContent = msgStr;
    entry.appendChild(prefix);
    entry.appendChild(content);
    terminal.appendChild(entry);
    terminal.scrollTop = terminal.scrollHeight;
}

// ─── Text Input Handler ────────────────────────────────────────────────────────

function submitTextInput() {
    const input = document.getElementById('text-input');
    if (!input) return;
    const query = input.value.trim();
    if (!query) return;
    input.value = '';
    eel.process_text_input(query)();
}

// ─── Session Reset ─────────────────────────────────────────────────────────────

function clearSession() {
    // Clear terminal
    const terminal = document.getElementById('terminal-log');
    if (terminal) terminal.innerHTML = '';

    // Clear chat window + restore welcome card
    const chatWindow = document.getElementById('chat-window');
    if (chatWindow) {
        chatWindow.innerHTML = `
            <div class="chat-welcome">
                <div class="welcome-icon">◈</div>
                <div class="welcome-text">F.R.I.D.A.Y. ONLINE</div>
                <div class="welcome-divider"></div>
                <div class="welcome-sub">Neural interface initialized. Awaiting your command, boss.</div>
            </div>`;
        _welcomeRemoved = false;
    }

    _thinkingBubble = null;
    eel.clear_session()();
}

// ─── Wake Word Functions ───────────────────────────────────────────────────────

eel.expose(updateWakeWordStatus);
function updateWakeWordStatus(status) {
    const pill    = document.getElementById('wake-word-pill');
    const label   = document.getElementById('ww-status');
    const btn     = document.getElementById('ww-toggle-btn');
    const sidebar = document.getElementById('sidebar-ww-status');

    if (!pill || !label) return;

    pill.classList.remove('ww-state-active', 'ww-state-standby', 'ww-state-off', 'ww-state-unavailable');

    const stateMap = {
        'active':      { cls: 'ww-state-active',      text: 'ACTIVE',      btn: 'DISABLE', sidebar: 'ACTIVE' },
        'standby':     { cls: 'ww-state-standby',     text: 'STANDBY',     btn: 'DISABLE', sidebar: 'STANDBY' },
        'off':         { cls: 'ww-state-off',          text: 'OFF',         btn: 'ENABLE',  sidebar: 'OFFLINE' },
        'unavailable': { cls: 'ww-state-unavailable',  text: 'UNAVAILABLE', btn: 'N/A',     sidebar: 'N/A' },
    };

    const state = stateMap[status] || stateMap['unavailable'];
    pill.classList.add(state.cls);
    label.textContent = state.text;

    if (btn) {
        btn.textContent = state.btn;
        if (status === 'active' || status === 'standby') btn.classList.add('ww-enabled');
        else btn.classList.remove('ww-enabled');
        btn.disabled = (status === 'unavailable');
    }

    if (sidebar) sidebar.textContent = state.sidebar;
}

function toggleWakeWord() {
    const label = document.getElementById('ww-status');
    if (!label) return;
    const currentStatus = label.textContent.trim();
    const shouldEnable  = (currentStatus === 'OFF' || currentStatus === 'UNAVAILABLE');
    eel.toggle_wake_word(shouldEnable)(function() {});
}

// ─── Keyboard Shortcuts ────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    const textInput = document.getElementById('text-input');
    if (textInput) {
        textInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submitTextInput();
            }
        });
    }

    // Initialise canvas
    resizeCanvas();
    animateCanvas();

    // Poll wake word status on startup
    setTimeout(() => {
        eel.get_wake_word_status()(function(status) {
            updateWakeWordStatus(status);
        });
    }, 1500);
});