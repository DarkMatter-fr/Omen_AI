"""
ears.py — Speech-to-Text input module for OMEN.

Handles microphone capture, ambient noise calibration, and
transcription via Google Web Speech API.
"""

import logging
import speech_recognition as sr
from modules import audio_utils as au

logger = logging.getLogger("OMEN.ears")

# Common phonetic mishearings of "OMEN" by Google STT.
# Future: replace with a custom trained language model or Porcupine wake word.
OMEN_ALIASES = [
    "women", "oh man", "amen", "roman", "almond",
    "oman", "open", "oh min", "a man"
]


def take_command() -> str:
    """
    Main sensory entry point.
    1. Samples ambient decibels to auto-calibrate recognition thresholds.
    2. Opens the microphone and listens for a voice command.
    3. Transcribes and normalizes the audio to a clean string.

    Returns:
        str: Lowercase transcribed query, or "none" on failure/silence.
    """
    r = sr.Recognizer()

    # --- Step 1: Ambient noise calibration ---
    db_level = au.scan_ambient_decibels()
    logger.debug(f"Ambient room level: {db_level} dB")

    if db_level < 45.0:
        detected_mode = "whisper"
        r.energy_threshold = 200
        r.pause_threshold = 1.2
    elif db_level >= 68.0:
        detected_mode = "aggressive"
        r.energy_threshold = 1250
        r.pause_threshold = 0.7
    else:
        detected_mode = "standard"
        r.energy_threshold = 450
        r.pause_threshold = 0.9

    logger.debug(f"Calibration mode: {detected_mode.upper()} (energy={r.energy_threshold})")

    # --- Step 2: Capture audio ---
    with sr.Microphone() as source:
        try:
            # Max 15s phrase to prevent memory bloat; 4s silence = timeout
            audio = r.listen(source, timeout=4, phrase_time_limit=15)
            logger.debug("Audio captured. Sending to STT engine...")

            # English-India locale for accurate syllable extraction
            query = r.recognize_google(audio, language='en-in').lower()

            # --- Step 3: Text normalization ---
            # Fix known STT quirk: 'tough' → 'tuff'
            query = query.replace("tough", "tuff")

            # Correct phonetic mishearings of the assistant name "OMEN"
            # Bug fix: iterate and check each alias, replace the MATCHED alias (not `alias` var)
            for alias in OMEN_ALIASES:
                if alias in query:
                    query = query.replace(alias, "omen")
                    logger.debug(f"Alias '{alias}' normalized to 'omen'")
                    break  # Stop after first match to avoid over-replacement

            logger.info(f"Transcribed query: '{query}'")
            return query

        except sr.WaitTimeoutError:
            logger.info("Timeout: No speech detected within the listening window.")
            return "none"
        except sr.UnknownValueError:
            logger.info("STT: Audio captured but speech was unintelligible.")
            return "none"
        except Exception as e:
            logger.error(f"STT pipeline failure: {e}")
            return "none"