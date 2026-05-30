const micWrapper = document.getElementById('mic-wrapper');
const transcript = document.getElementById('transcript');
const hud = document.getElementById('hud');
const statusLabel = document.getElementById('status-label');
const waveformCanvas = document.getElementById('waveform');
const canvasCtx = waveformCanvas.getContext('2d');

let currentAssistantState = 'idle';
let animationFrameId = null;

/* --- EXPOSED TO PYTHON VIA EEL --- */

// Standard UI state modifier
eel.expose(setAssistantState);
function setAssistantState(state) {
    micWrapper.className = `orb-wrapper ${state}`;
    hud.className = `hud ${state}`;
    statusLabel.textContent = state.toUpperCase();
    currentAssistantState = state;
}

// Append conversation text bubbles
eel.expose(addMessage);
function addMessage(role, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `msg ${role}`;
    const now = new Date();
    const time = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
    msgDiv.innerHTML = `<span>${text}</span><span class="time">${time}</span>`;
    transcript.appendChild(msgDiv);
    transcript.scrollTop = transcript.scrollHeight;
}

// Interactive "Tuff Mode" Visual Trigger
eel.expose(triggerTuffMode);
function triggerTuffMode(duration) {
    const prevState = currentAssistantState;
    
    micWrapper.className = `orb-wrapper tuff`;
    hud.className = `hud tuff`;
    statusLabel.textContent = "TUFF MODE ACTIVE";
    statusLabel.style.color = "#ff4500";

    setTimeout(() => {
        setAssistantState(prevState);
        statusLabel.style.color = ""; 
    }, duration);
}

/* --- LOCAL ACTIONS --- */

function triggerMic() {
    console.log("[Eel JS] Orb Clicked -> Initiating Python Voice Capture Pipeline");
    eel.process_voice_input();
}

/* Waveform Canvas Rendering Loop */
/* Spectral Waveform Canvas Rendering Loop */
/* Premium Native Waveform Canvas Rendering Loop */
function drawWaveform() {
    animationFrameId = requestAnimationFrame(drawWaveform);
    const w = waveformCanvas.width, h = waveformCanvas.height;
    canvasCtx.clearRect(0, 0, w, h);
    canvasCtx.beginPath();
    canvasCtx.moveTo(0, h / 2);
    
    // Core OMEN Brand Color Mapping
    let strokeColor = 'rgba(107, 104, 128, 0.3)'; // IDLE (Muted Grey Slate)
    if (currentAssistantState === 'listening') strokeColor = 'rgba(232, 64, 87, 0.85)';
    if (currentAssistantState === 'thinking') strokeColor = 'rgba(107, 33, 168, 0.85)';
    if (currentAssistantState === 'speaking') strokeColor = 'rgba(34, 211, 238, 0.85)';
    if (micWrapper.classList.contains('tuff')) strokeColor = 'rgba(255, 69, 0, 1)';

    canvasCtx.strokeStyle = strokeColor;
    canvasCtx.lineWidth = 2;
    const t = Date.now() * 0.003;
    
    for (let x = 0; x < w; x++) {
        let amplitude = 2;
        if (currentAssistantState === 'listening') amplitude = 14;
        if (currentAssistantState === 'speaking') amplitude = 20;
        if (micWrapper.classList.contains('tuff')) amplitude = 26;

        const y = (h / 2) + Math.sin(x * 0.018 + t) * Math.cos(x * 0.006 + t) * amplitude;
        canvasCtx.lineTo(x, y);
    }
    canvasCtx.stroke();
}
// Run visualizer immediately on page load
drawWaveform();