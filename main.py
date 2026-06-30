"""
main.py — OMEN OS Orchestration Layer

This is the central nervous system. It:
  1. Initializes the Eel UI framework
  2. Sets up the global logging pipeline
  3. Exposes Python functions to the JavaScript bridge
  4. Dispatches tool calls returned by the AI brain
  5. Manages the voice I/O loop
"""

import os
import logging
import subprocess
import asyncio
import threading
from datetime import datetime
import pyautogui

# pyrefly: ignore [missing-import]
import eel

# Local modules
from modules.ears import take_command
from modules.mouth import speak
from modules.brain import generate_response, reset_conversation, send_tool_results
from modules.web import (
    get_world_news, get_world_finance_news,
    open_world_monitor, open_finance_world_monitor
)
import modules.memory as memory
from modules.wake_word import WakeWordListener

# ---------------------------------------------------------------------------
# 1. LOGGING SETUP
# ---------------------------------------------------------------------------

_log_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'logs')
os.makedirs(_log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        # Console output
        logging.StreamHandler(),
        # Persistent log file (structured, rotatable)
        logging.FileHandler(
            os.path.join(_log_dir, 'omen.log'),
            encoding='utf-8'
        )
    ]
)

logger = logging.getLogger("OMEN.main")


# ---------------------------------------------------------------------------
# 2. EEL INITIALIZATION
# ---------------------------------------------------------------------------

current_dir = os.path.dirname(os.path.realpath(__file__))
web_dir = os.path.join(current_dir, 'web')
eel.init(web_dir)


# ---------------------------------------------------------------------------
# 2b. MEMORY INITIALISATION
# ---------------------------------------------------------------------------

memory.init_memory()
logger.info("Memory subsystem ready.")


# ---------------------------------------------------------------------------
# 2c. WAKE WORD SUBSYSTEM INITIALISATION
# ---------------------------------------------------------------------------

# Event: listener thread sets this when wake word is detected
_wake_event = threading.Event()

# Event: main logic sets this while processing a command (suppresses re-trigger)
_is_processing = threading.Event()

# The wake word listener daemon thread
_wake_listener = WakeWordListener(
    wake_event=_wake_event,
    is_processing=_is_processing,
)
_wake_listener.start()
logger.info("Wake word listener thread started.")


def _wake_word_poll_loop() -> None:
    """
    Polls the _wake_event in a background daemon thread.
    When the wake word is detected:
      1. Clears the event.
      2. Sets _is_processing to suppress re-triggering.
      3. Updates the UI indicator.
      4. Opens the mic via take_command() and processes the query.
      5. Clears _is_processing when done.
    """
    logger.info("Wake word poll loop started.")
    while True:
        # Block until the listener signals a wake event
        _wake_event.wait()
        _wake_event.clear()

        # Guard: do not double-trigger
        if _is_processing.is_set():
            logger.debug("Wake event ignored — already processing.")
            continue

        logger.info("Wake event received — activating microphone.")
        _log_ui("[WAKE WORD] Trigger detected. Listening...")
        _update_wake_status()

        # Hand off to voice capture + full pipeline
        eel.setAssistantState('listening')()
        query = take_command()

        if query and query.strip() not in ("", "none"):
            _process_query(query)
        else:
            _log_ui("[WAKE WORD] No speech captured after wake trigger.")
            eel.setAssistantState('idle')()

        _update_wake_status()


# Start the poll loop as a daemon thread (exits when main exits)
_poll_thread = threading.Thread(
    target=_wake_word_poll_loop,
    name="WakeWordPollLoop",
    daemon=True,
)
_poll_thread.start()
logger.info("Wake word poll loop thread started.")


# ---------------------------------------------------------------------------
# 3. INTERACTION LOG (Command Stack)
# ---------------------------------------------------------------------------

def stack_call(actor: str, message: str) -> None:
    """
    Write an interaction to the human-readable command stack log.
    This is separate from the structured omen.log — it's a plain
    transcript for easy reading and session replay.
    """
    log_file = os.path.join(_log_dir, 'command_stack.txt')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {actor}: {message}\n")


# ---------------------------------------------------------------------------
# 4. TOOL DISPATCHER
# ---------------------------------------------------------------------------

# Tools that return data and need results fed back to Gemini for a spoken response.
_DATA_TOOLS = {"get_world_news", "get_world_finance_news"}


def _collect_tool_results(function_calls) -> tuple[dict, list]:
    """
    Execute data-returning tools and collect their output.
    Action tools (software, media, monitors) are returned separately
    for immediate fire-and-forget dispatch.

    Returns:
        (tool_results: dict, action_calls: list)
        tool_results  — {tool_name: result_string} for data tools
        action_calls  — FunctionCall list for fire-and-forget tools
    """
    tool_results = {}
    action_calls = []

    for fc in function_calls:
        name = fc.name
        logger.info(f"Collecting tool result: {name}")

        # --- DATA TOOL: Global News ---
        if name == "get_world_news":
            stack_call("SYSTEM", "Fetching global RSS feeds")
            _log_ui("ACTION: Accessing global RSS feeds...")
            try:
                news_data = asyncio.run(get_world_news())
                _log_ui("STATUS: Global intelligence acquired.")
                _log_ui(news_data)
                tool_results[name] = news_data
            except Exception as e:
                logger.error(f"News fetch failed: {e}")
                _log_ui(f"ERROR: News feed unreachable — {e}")
                tool_results[name] = "News feed is unresponsive right now."

        # --- DATA TOOL: Finance News ---
        elif name == "get_world_finance_news":
            stack_call("SYSTEM", "Fetching finance RSS feeds")
            _log_ui("ACTION: Accessing market data feeds...")
            try:
                finance_data = asyncio.run(get_world_finance_news())
                _log_ui("STATUS: Market intelligence acquired.")
                _log_ui(finance_data)
                tool_results[name] = finance_data
            except Exception as e:
                logger.error(f"Finance feed fetch failed: {e}")
                _log_ui(f"ERROR: Finance feed unreachable — {e}")
                tool_results[name] = "Finance feed is unresponsive right now."

        # --- ACTION TOOL: defer to _dispatch_action_calls ---
        else:
            action_calls.append(fc)

    return tool_results, action_calls


def _dispatch_action_calls(function_calls) -> None:
    """
    Execute fire-and-forget action tool calls.
    These do not return data to Gemini — they perform side effects only.
    """
    for function_call in function_calls:
        name = function_call.name
        args = function_call.args or {}
        logger.info(f"Dispatching action tool: {name} | args: {args}")

        # --- TOOL: Software Launcher ---
        if name == "open_software":
            target_app = args.get("app_name", "")
            stack_call("SYSTEM", f"Launching application: {target_app}")
            _log_ui(f"ACTION: Launching [{target_app}]...")
            try:
                # Use Popen (non-blocking) with a plain string command for Windows shell
                subprocess.Popen(f"start {target_app}", shell=True)
                _log_ui(f"STATUS: [{target_app}] launched successfully.")
                speak(f"Booting up {target_app} for you now, boss.")
            except Exception as e:
                logger.error(f"Software launch failed for '{target_app}': {e}")
                _log_ui(f"ERROR: Could not launch [{target_app}].")
                speak("I hit a snag trying to launch that application, boss.")

        # --- TOOL: Media Controls ---
        elif name == "open_media":
            action = args.get("action", "")
            amount = int(args.get("amount", 5))
            stack_call("SYSTEM", f"Media control: {action} x{amount}")
            _log_ui(f"ACTION: Media keystroke [{action}] x{amount}")
            try:
                if action in ("play", "pause"):
                    pyautogui.press("playpause")
                elif action == "stop":
                    pyautogui.press("stop")
                elif action == "next":
                    pyautogui.press("nexttrack")
                elif action == "previous":
                    pyautogui.press("prevtrack")
                elif action == "volume_up":
                    for _ in range(amount):
                        pyautogui.press("volumeup")
                elif action == "volume_down":
                    for _ in range(amount):
                        pyautogui.press("volumedown")
                elif action == "mute":
                    pyautogui.press("volumemute")
                else:
                    logger.warning(f"Unknown media action: '{action}'")
                _log_ui("STATUS: Media control executed.")
            except Exception as e:
                logger.error(f"Media control failed: {e}")
                _log_ui(f"ERROR: Media control failed — {e}")

        # --- TOOL: World Monitor UI ---
        elif name == "open_world_monitor":
            stack_call("SYSTEM", "Opening world monitor")
            _log_ui("ACTION: Initializing World Monitor...")
            try:
                msg = asyncio.run(open_world_monitor())
                _log_ui("STATUS: Monitor initialized.")
                speak(msg)
            except Exception as e:
                logger.error(f"World monitor failed: {e}")

        # --- TOOL: Finance Monitor UI ---
        elif name == "open_finance_world_monitor":
            stack_call("SYSTEM", "Opening finance monitor")
            _log_ui("ACTION: Initializing Finance Monitor...")
            try:
                msg = asyncio.run(open_finance_world_monitor())
                _log_ui("STATUS: Finance monitor initialized.")
                speak(msg)
            except Exception as e:
                logger.error(f"Finance monitor failed: {e}")

        else:
            logger.warning(f"Unknown tool call received: '{name}'")


# ---------------------------------------------------------------------------
# 5. CORE PROCESSING FUNCTION (shared by voice + text input)
# ---------------------------------------------------------------------------

def _process_query(query: str) -> None:
    """
    Process any user query (from voice or text input) through the full pipeline:
    Brain → Agentic Tool Loop → Speech Output → UI Update.

    Sets _is_processing for the duration so the wake word listener
    does not re-trigger while OMEN is speaking or thinking.
    The finally block guarantees _is_processing is ALWAYS cleared,
    even on early return, exception, or error string fallback.

    Agentic loop:
      Round 1: Gemini sees the query → may return function_calls (no spoken text yet).
      Round 2: Data tool results fed back → Gemini generates the spoken brief.
      Round 2+: Any follow-up action calls (e.g. open_world_monitor) dispatched.
    """
    if not query or query.strip() in ("", "none"):
        eel.setAssistantState('idle')()
        return

    # Block wake word re-triggering while processing
    _is_processing.set()
    _update_wake_status()

    try:
        # Log and display user input
        stack_call("USER", query)
        _log_ui(f"YOU: {query}")

        eel.setAssistantState('thinking')()
        _log_ui("Processing via F.R.I.D.A.Y. mainframe...")

        response = generate_response(query)

        # --- Handle plain text fallback (error string from brain) ---
        if isinstance(response, str):
            stack_call("F.R.I.D.A.Y.", response)
            _log_ui(f"F.R.I.D.A.Y: {response}")
            speak(response)
            return  # finally block will still clear _is_processing

        # --- Speak any immediate text (non-tool conversational responses) ---
        if hasattr(response, 'text') and response.text:
            clean = response.text.replace("*", "").replace("#", "").strip()
            if clean:
                stack_call("F.R.I.D.A.Y.", clean)
                _log_ui(f"F.R.I.D.A.Y: {clean}")
                speak(clean)

        # --- Agentic tool loop ---
        if hasattr(response, 'function_calls') and response.function_calls:
            # Step 1: Separate data tools (need results fed back) from action tools
            tool_results, action_calls = _collect_tool_results(response.function_calls)

            # Step 2: Dispatch any immediate action tools (software, media)
            if action_calls:
                _dispatch_action_calls(action_calls)

            # Step 3: Feed data results back to Gemini → get the spoken response
            if tool_results:
                spoken, follow_up_calls = send_tool_results(response, tool_results)
                if spoken:
                    clean = spoken.replace("*", "").replace("#", "").strip()
                    if clean:
                        stack_call("F.R.I.D.A.Y.", clean)
                        _log_ui(f"F.R.I.D.A.Y: {clean}")
                        speak(clean)

                # Step 4: Dispatch any follow-up action calls from the spoken response
                # (e.g. Gemini calls open_world_monitor after delivering the news brief)
                if follow_up_calls:
                    _dispatch_action_calls(follow_up_calls)

    except Exception as e:
        logger.error(f"_process_query pipeline error: {e}")
        _log_ui(f"ERROR: Pipeline failure — {e}")

    finally:
        # ALWAYS release the processing lock and restore idle state,
        # regardless of how the function exits (return, exception, or normal).
        eel.setAssistantState('idle')()
        _is_processing.clear()
        _update_wake_status()


# ---------------------------------------------------------------------------
# 6. EEL-EXPOSED FUNCTIONS (Python → JS bridge)
# ---------------------------------------------------------------------------

def _log_ui(message: str) -> None:
    """Helper: safely send a log message to the UI terminal."""
    try:
        eel.logToTerminal(str(message))()
    except Exception as e:
        logger.warning(f"UI log failed (UI may not be ready): {e}")


def _update_wake_status() -> None:
    """Helper: push current wake word listener status to the UI pill."""
    try:
        status = _wake_listener.get_status()
        eel.updateWakeWordStatus(status)()
    except Exception as e:
        logger.debug(f"Wake status UI update skipped (UI may not be ready): {e}")


@eel.expose
def process_voice_input() -> None:
    """Called by UI button click — captures microphone and processes voice."""
    eel.setAssistantState('listening')()
    _log_ui("Microphone active. Awaiting input...")

    query = take_command()

    if query == "none" or not query:
        _log_ui("No speech detected. Standing by.")
        eel.setAssistantState('idle')()
        return

    logger.info(f"Voice input received: '{query}'")
    _process_query(query)


@eel.expose
def process_text_input(text: str) -> None:
    """Called by UI text input — processes typed queries directly."""
    query = text.strip()
    if not query:
        return
    logger.info(f"Text input received: '{query}'")
    _process_query(query)


@eel.expose
def clear_session() -> None:
    """Reset the conversation history for a fresh session."""
    reset_conversation()  # brain.py handles semantic commit + new session ID
    _log_ui("Session cleared. Ready for a new conversation, boss.")
    logger.info("Session reset by user.")


@eel.expose
def get_memory_stats() -> dict:
    """
    Return current memory usage statistics for the UI status bar.
    Exposes: total turns stored, total sessions, semantic memory documents.
    """
    return memory.get_stats()


@eel.expose
def toggle_wake_word(enabled: bool) -> None:
    """
    Enable or disable the continuous wake word listener from the UI.
    When disabled, the listener thread is stopped and resources are released.
    When re-enabled, a new listener thread is started.
    """
    global _wake_listener, _poll_thread

    if enabled:
        if not _wake_listener.is_alive():
            logger.info("Re-enabling wake word listener via UI toggle.")
            _wake_listener = WakeWordListener(
                wake_event=_wake_event,
                is_processing=_is_processing,
            )
            _wake_listener.start()
            _log_ui("[WAKE WORD] Continuous listening ENABLED.")
        else:
            logger.debug("Wake word listener already running — toggle ignored.")
    else:
        logger.info("Disabling wake word listener via UI toggle.")
        _wake_listener.stop()
        _log_ui("[WAKE WORD] Continuous listening DISABLED.")

    _update_wake_status()


@eel.expose
def get_wake_word_status() -> str:
    """
    Return the current wake word listener status for the UI pill.

    Returns:
        str: 'active' | 'standby' | 'off' | 'unavailable'
    """
    return _wake_listener.get_status()


# ---------------------------------------------------------------------------
# 7. ENTRY POINT
# ---------------------------------------------------------------------------

logger.info("=" * 60)
logger.info("OMEN OS — F.R.I.D.A.Y. Orchestration Layer Starting")
logger.info("=" * 60)

eel.start('index.html', size=(1400, 800))