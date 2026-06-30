"""
mouth.py — Text-to-Speech output module for OMEN.

Handles all voice synthesis. The engine is initialized once per call
to avoid thread-locking issues with pyttsx3's single-threaded driver.
"""

import pyttsx3
import time
import logging

logger = logging.getLogger("OMEN.mouth")

# Slang normalization map — applied before speaking
SLANG_MAP = {
    "tough": "tuff",
    "top": "tuff",
    "stuff": "tuff"
}


def clean_text(text: str) -> str:
    """Remove markdown artifacts and normalize slang before speaking."""
    # Strip markdown formatting
    text = text.replace("*", "").replace("#", "").replace("`", "")
    # Normalize known slang
    words = text.split()
    cleaned = [SLANG_MAP.get(w.lower(), w) for w in words]
    return " ".join(cleaned)


def speak(audio: str) -> None:
    """
    Synthesize and play speech for the given text.
    Initializes the pyttsx3 engine fresh each call to prevent
    cross-call state corruption on Windows SAPI.
    """
    if not audio or not audio.strip():
        logger.warning("speak() called with empty string — skipping.")
        return

    processed_audio = clean_text(audio)
    logger.info(f"OMEN speaking: {processed_audio}")

    try:
        engine = pyttsx3.init()

        # Voice configuration
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)
        engine.setProperty('rate', 200)

        # Speak once — do NOT call say/runAndWait more than once per init
        engine.say(processed_audio)
        engine.runAndWait()

    except Exception as e:
        logger.error(f"TTS engine failure: {e}")
    finally:
        try:
            engine.stop()
        except Exception:
            pass

    # Brief pause to allow audio driver to release cleanly
    time.sleep(0.05)