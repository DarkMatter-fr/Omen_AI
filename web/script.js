/* ==========================================
   OMEN OS — JAVASCRIPT BRIDGE (script.js)
   ========================================== */

/**
 * 1. ASSISTANT STATE ENGINE
 * Python calls this to animate the central core orb based on current state.
 * @param {string} state - 'idle' | 'listening' | 'thinking'
 */
eel.expose(setAssistantState);
function setAssistantState(state) {
    const visualizer = document.getElementById('visualizer');
    if (visualizer) {
        visualizer.className = 'visualizer ' + state;
    }

    // Disable the mic button while OMEN is processing
    const micBtn = document.getElementById('mic-btn');
    if (micBtn) {
        micBtn.disabled = (state === 'listening' || state === 'thinking');
    }
}

/**
 * 2. HOLOGRAPHIC TERMINAL LOGGER
 * Python calls this to print system status to the UI console.
 * Uses textContent instead of innerHTML to prevent XSS injection.
 * @param {string} message - The log string to display
 */
eel.expose(logToTerminal);
function logToTerminal(message) {
    const terminal = document.getElementById('terminal-log');
    if (!terminal) return;

    const entry = document.createElement('p');

    // Prefix indicator — color-coded by type
    const prefix = document.createElement('span');
    prefix.className = 'log-prefix';
    prefix.textContent = '> ';

    const content = document.createElement('span');

    // Color-code log lines by actor
    const msgStr = String(message);
    if (msgStr.startsWith('YOU:')) {
        entry.classList.add('log-user');
    } else if (msgStr.startsWith('F.R.I.D.A.Y:')) {
        entry.classList.add('log-friday');
    } else if (msgStr.startsWith('ERROR:')) {
        entry.classList.add('log-error');
    } else if (msgStr.startsWith('ACTION:') || msgStr.startsWith('STATUS:')) {
        entry.classList.add('log-system');
    }

    // Safe text insertion — no innerHTML, no XSS
    content.textContent = msgStr;
    entry.appendChild(prefix);
    entry.appendChild(content);
    terminal.appendChild(entry);

    // Auto-scroll to latest entry
    terminal.scrollTop = terminal.scrollHeight;
}

/**
 * 3. TEXT INPUT HANDLER
 * Sends the typed query to Python for processing.
 */
function submitTextInput() {
    const input = document.getElementById('text-input');
    if (!input) return;

    const query = input.value.trim();
    if (!query) return;

    input.value = '';
    eel.process_text_input(query)();
}

/**
 * 4. SESSION RESET
 * Clears conversation history in the brain and the UI terminal.
 */
function clearSession() {
    const terminal = document.getElementById('terminal-log');
    if (terminal) {
        terminal.innerHTML = '';
    }
    eel.clear_session()();
}

/**
 * 5. KEYBOARD SHORTCUT: Enter to submit text input
 */
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

    // Poll Python for wake word status on startup (once UI is ready)
    setTimeout(() => {
        eel.get_wake_word_status()(function(status) {
            updateWakeWordStatus(status);
        });
    }, 1500);
});


/**
 * 6. WAKE WORD STATUS — Python calls this to update the UI pill
 * Called by Python's _update_wake_status() helper via Eel.
 * @param {string} status - 'active' | 'standby' | 'off' | 'unavailable'
 */
eel.expose(updateWakeWordStatus);
function updateWakeWordStatus(status) {
    const pill    = document.getElementById('wake-word-pill');
    const dot     = document.getElementById('ww-dot');
    const label   = document.getElementById('ww-status');
    const btn     = document.getElementById('ww-toggle-btn');
    const sidebar = document.getElementById('sidebar-ww-status');

    if (!pill || !label) return;

    // Remove all state classes
    pill.classList.remove(
        'ww-state-active', 'ww-state-standby',
        'ww-state-off', 'ww-state-unavailable'
    );

    // Map status to display values
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
        // Style toggle button: DISABLE = red variant, ENABLE = default
        if (status === 'active' || status === 'standby') {
            btn.classList.add('ww-enabled');
        } else {
            btn.classList.remove('ww-enabled');
        }
        // Disable the button if OWW is unavailable
        btn.disabled = (status === 'unavailable');
    }

    if (sidebar) {
        sidebar.textContent = state.sidebar;
    }
}


/**
 * 7. WAKE WORD TOGGLE — Called by the pill's toggle button click
 * Reads current state and sends inverse to Python.
 */
function toggleWakeWord() {
    const label = document.getElementById('ww-status');
    if (!label) return;

    const currentStatus = label.textContent.trim();
    // If currently active or standby, disable. Otherwise enable.
    const shouldEnable = (currentStatus === 'OFF' || currentStatus === 'UNAVAILABLE') ? true : false;

    eel.toggle_wake_word(shouldEnable)(function(result) {
        // Python will call updateWakeWordStatus() after toggling
    });
}