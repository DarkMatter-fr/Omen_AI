"""
mouth.py — Text-to-Speech output module for OMEN.

Primary engine: edge-tts (Microsoft neural voices — no API key required).
Fallback engine: pyttsx3 (offline SAPI, used when edge-tts is unavailable).

Voice / rate are configurable via environment variables:
  EDGE_TTS_VOICE  — e.g. "en-US-AriaNeural" (default)
  EDGE_TTS_RATE   — e.g. "+15%"  (default: "+10%", positive = faster)
"""

import asyncio
import logging
import os
import tempfile
import time

import pyttsx3
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

logger = logging.getLogger("OMEN.mouth")

# ---------------------------------------------------------------------------
# Configuration (overridable via .env)
# ---------------------------------------------------------------------------

_EDGE_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AriaNeural")
_EDGE_RATE  = os.getenv("EDGE_TTS_RATE",  "+10%")

# ---------------------------------------------------------------------------
# Text pre-processing
# ---------------------------------------------------------------------------

# Slang normalization map — applied before speaking
SLANG_MAP = {
    "tough": "tuff",
    "top":   "tuff",
    "stuff": "tuff",
}


def clean_text(text: str) -> str:
    """Remove markdown artifacts and normalize slang before speaking."""
    text = text.replace("*", "").replace("#", "").replace("`", "")
    words  = text.split()
    cleaned = [SLANG_MAP.get(w.lower(), w) for w in words]
    return " ".join(cleaned)


# ---------------------------------------------------------------------------
# Edge-TTS (primary)
# ---------------------------------------------------------------------------

async def _speak_edge_async(text: str) -> None:
    """
    Generate speech via Microsoft Edge TTS and play it.

    Writes audio to a named temp file (.mp3) then plays it with playsound.
    The temp file is deleted after playback regardless of errors.
    """
    import edge_tts
    from playsound import playsound

    communicate = edge_tts.Communicate(text, voice=_EDGE_VOICE, rate=_EDGE_RATE)

    # NamedTemporaryFile with delete=False because Windows can't delete open files
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await communicate.save(tmp_path)
        playsound(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _speak_edge_sync(text: str) -> None:
    """Blocking wrapper around the async edge-tts coroutine."""
    asyncio.run(_speak_edge_async(text))


# ---------------------------------------------------------------------------
# pyttsx3 (fallback)
# ---------------------------------------------------------------------------

def _speak_pyttsx3(text: str) -> None:
    """
    Synthesize and play speech via pyttsx3 (Windows SAPI).
    Engine is re-initialized each call to prevent cross-call state corruption.
    """
    engine = pyttsx3.init()
    try:
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)
        engine.setProperty('rate', 200)
        engine.say(text)
        engine.runAndWait()
    except Exception:
        raise
    finally:
        try:
            engine.stop()
        except Exception:
            pass
    time.sleep(0.05)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def speak(audio: str) -> None:
    """
    Synthesize and play speech for the given text.

    Tries edge-tts first (neural, human-quality Microsoft voices).
    Falls back to pyttsx3 automatically if edge-tts fails for any reason
    (no internet, service timeout, dependency error, etc.).
    """
    if not audio or not audio.strip():
        logger.warning("speak() called with empty string — skipping.")
        return

    processed = clean_text(audio)
    logger.info(f"OMEN speaking: {processed[:80]}{'...' if len(processed) > 80 else ''}")

    # --- Primary: edge-tts ---
    try:
        _speak_edge_sync(processed)
        logger.debug("edge-tts playback complete.")
        return
    except Exception as e:
        logger.warning(f"edge-tts failed ({e}), falling back to pyttsx3.")

    # --- Fallback: pyttsx3 ---
    try:
        _speak_pyttsx3(processed)
        logger.debug("pyttsx3 fallback playback complete.")
    except Exception as e:
        logger.error(f"pyttsx3 fallback also failed: {e}")