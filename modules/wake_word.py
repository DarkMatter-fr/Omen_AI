"""
wake_word.py — Always-On Wake Word Listener for OMEN OS (Milestone 2)

Runs OpenWakeWord in a background daemon thread, continuously sampling
the microphone and signaling via threading.Event when the wake phrase
is detected. Designed to be non-blocking and resource-safe.

Architecture:
  WakeWordListener (Thread)
      └── PyAudio @ 16kHz / 1280-frame chunks
              └── OWW model.predict() every ~80ms
                      └── score > threshold → wake_event.set()
"""

import os
import logging
import threading

logger = logging.getLogger("OMEN.wake_word")

# ---------------------------------------------------------------------------
# Optional imports — graceful degradation if OWW not installed
# ---------------------------------------------------------------------------

try:
    import pyaudio
    import numpy as np
    # pyrefly: ignore [missing-import]
    from openwakeword.model import Model as OWWModel
    _OWW_AVAILABLE = True
except ImportError as e:
    _OWW_AVAILABLE = False
    logger.warning(f"OpenWakeWord not available: {e}. Wake word detection disabled.")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHUNK_SIZE       = 1280    # OWW requires exactly 1280 samples per frame
SAMPLE_RATE      = 16000   # OWW requires 16 kHz mono audio
CHANNELS         = 1
DETECT_THRESHOLD = 0.5     # Confidence score to trigger wake event (0.0-1.0)

# Custom model path — drop hey_omen.onnx here to upgrade from built-in
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOM_MODEL_PATH = os.path.join(_PROJECT_ROOT, "data", "models", "hey_omen.onnx")

# Built-in fallback model — must match a key in openwakeword.MODELS registry
BUILTIN_MODEL = "hey_jarvis_v0.1"


# ---------------------------------------------------------------------------
# WakeWordListener — background daemon thread
# ---------------------------------------------------------------------------

class WakeWordListener(threading.Thread):
    """
    Continuously listens for the OMEN wake word in a daemon thread.

    Usage:
        listener = WakeWordListener(wake_event, is_processing)
        listener.start()    # starts the background thread
        listener.stop()     # graceful shutdown + resource release

    Args:
        wake_event (threading.Event): Set by this thread when the wake word
                                       is detected. Main thread clears it
                                       after handling the event.
        is_processing (threading.Event): When set, listener suppresses
                                          detection (OMEN already active).
    """

    def __init__(
        self,
        wake_event: threading.Event,
        is_processing: threading.Event,
    ):
        super().__init__(name="WakeWordListener", daemon=True)
        self._wake_event      = wake_event
        self._is_processing   = is_processing
        self._running         = False
        self._available       = _OWW_AVAILABLE
        self._status          = "off"     # "active" | "standby" | "off"
        self._model           = None
        self._pa              = None
        self._stream          = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Signal the listener to stop and release all audio resources."""
        logger.info("WakeWordListener: Stop requested.")
        self._running = False
        self._status  = "off"

    def get_status(self) -> str:
        """
        Return current listener state for the UI pill indicator.

        Returns:
            str: 'active' | 'standby' | 'off' | 'unavailable'
        """
        if not self._available:
            return "unavailable"
        if self._is_processing.is_set():
            return "standby"
        return self._status

    def is_available(self) -> bool:
        """Return True if OpenWakeWord is installed and listener can operate."""
        return self._available

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_model(self) -> bool:
        """
        Load OWW model. Prefers custom hey_omen.onnx; falls back to built-in.
        Auto-downloads the built-in model on first run if the file is missing.

        Returns:
            bool: True if model loaded successfully.
        """
        try:
            os.makedirs(os.path.join(_PROJECT_ROOT, "data", "models"), exist_ok=True)

            if os.path.isfile(CUSTOM_MODEL_PATH):
                logger.info(f"Loading custom wake word model: {CUSTOM_MODEL_PATH}")
                self._model = OWWModel(
                    wakeword_models=[CUSTOM_MODEL_PATH],
                    inference_framework="onnx"
                )
                logger.info("Custom 'hey_omen' model loaded successfully.")
            else:
                logger.info(f"Custom model not found at {CUSTOM_MODEL_PATH}")
                logger.info(f"Loading built-in fallback: '{BUILTIN_MODEL}'")

                # Ensure model files are present — downloads only if missing (self-healing)
                import openwakeword.utils
                logger.info("Checking OWW model files (will download if missing)...")
                openwakeword.utils.download_models([BUILTIN_MODEL])
                logger.info("OWW model files ready.")

                self._model = OWWModel(
                    wakeword_models=[BUILTIN_MODEL],
                    inference_framework="onnx"
                )
                logger.info(f"Built-in '{BUILTIN_MODEL}' model loaded successfully.")

            return True

        except Exception as e:
            logger.error(f"Failed to load OWW model: {e}")
            return False

    def _open_audio_stream(self) -> bool:
        """
        Initialize PyAudio and open the microphone stream at 16kHz.

        Returns:
            bool: True if stream opened successfully.
        """
        try:
            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )
            logger.info("Wake word audio stream opened (16kHz mono, 1280-frame chunks).")
            return True
        except Exception as e:
            logger.error(f"Failed to open audio stream for wake word: {e}")
            return False

    def _close_resources(self) -> None:
        """Cleanly shut down PyAudio stream and terminate PA instance."""
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
                logger.debug("Wake word audio stream closed.")
        except Exception as e:
            logger.warning(f"Error closing audio stream: {e}")

        try:
            if self._pa:
                self._pa.terminate()
                self._pa = None
                logger.debug("PyAudio instance terminated.")
        except Exception as e:
            logger.warning(f"Error terminating PyAudio: {e}")

    # ------------------------------------------------------------------
    # Main thread loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Daemon thread entry point. Loops indefinitely, processing 80ms
        audio chunks through OWW until stop() is called.
        """
        if not self._available:
            logger.warning("OWW unavailable — wake word listener not starting.")
            self._status = "off"
            return

        # Step 1: Load model (may trigger first-run download)
        if not self._load_model():
            self._status = "off"
            return

        # Step 2: Open audio stream
        if not self._open_audio_stream():
            self._status = "off"
            return

        self._running = True
        self._status  = "active"
        logger.info("=" * 55)
        logger.info("OMEN WAKE WORD LISTENER: ACTIVE")
        logger.info(f"  Trigger model  : '{BUILTIN_MODEL}' (or custom if loaded)")
        logger.info(f"  Threshold      : {DETECT_THRESHOLD}")
        logger.info(f"  Frame size     : {CHUNK_SIZE} samples @ {SAMPLE_RATE}Hz (~80ms)")
        logger.info("=" * 55)

        try:
            while self._running:
                # Read one 80ms audio frame from mic
                try:
                    raw = self._stream.read(CHUNK_SIZE, exception_on_overflow=False)
                except Exception as e:
                    logger.warning(f"Audio read error (non-fatal): {e}")
                    continue

                # Suppress detection while OMEN is already processing
                if self._is_processing.is_set():
                    self._status = "standby"
                    continue
                else:
                    if self._status != "active":
                        self._status = "active"

                # Convert raw bytes to int16 array for OWW inference
                audio_frame = np.frombuffer(raw, dtype=np.int16)

                # Run OWW model inference
                try:
                    prediction = self._model.predict(audio_frame)
                except Exception as e:
                    logger.error(f"OWW inference error: {e}")
                    continue

                # Check confidence scores across all loaded models
                for model_name, score in prediction.items():
                    if score >= DETECT_THRESHOLD:
                        logger.info(
                            f"[WAKE WORD DETECTED] model='{model_name}' "
                            f"score={score:.3f} >= threshold={DETECT_THRESHOLD}"
                        )
                        # Signal the polling thread in main.py
                        self._wake_event.set()
                        # Brief pause to avoid re-triggering on the same utterance
                        threading.Event().wait(1.5)
                        break  # One detection event per inference cycle

        except Exception as e:
            logger.error(f"Wake word listener crashed unexpectedly: {e}")
        finally:
            self._status = "off"
            self._close_resources()
            logger.info("Wake word listener stopped and all resources released.")
