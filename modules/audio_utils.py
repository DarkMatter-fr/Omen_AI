"""
audio_utils.py — Shared audio hardware utilities for OMEN.

Provides low-level microphone sampling used by the ears module
to calibrate recognition thresholds before listening.
"""

import logging
import math
import numpy as np
import speech_recognition as sr

logger = logging.getLogger("OMEN.audio_utils")


def scan_ambient_decibels() -> float:
    """
    SHARED UTILITY: Samples the default microphone for 0.5 seconds
    and returns the ambient room noise level in decibels (dBFS).

    Returns:
        float: Decibel level (0.0 on silence or error, positive on noise).
               Falls back to 45.0 dB (standard threshold) on hardware failure.
    """
    r = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            audio_data = r.record(source, duration=0.5)
            raw_bytes = audio_data.get_raw_data()

            if not raw_bytes:
                logger.warning("Microphone returned empty audio buffer.")
                return 0.0

            samples = np.frombuffer(raw_bytes, dtype=np.int16)
            rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))

            if rms == 0:
                logger.debug("RMS is zero — completely silent environment.")
                return 0.0

            db = round(20 * math.log10(rms), 2)
            logger.debug(f"Ambient dB scan result: {db} dB")
            return db

        except Exception as e:
            logger.error(f"Ambient scan failed: {e}. Defaulting to 45.0 dB.")
            return 45.0  # Safe baseline fallback (standard mode)
