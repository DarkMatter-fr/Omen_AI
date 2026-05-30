import numpy as np
import speech_recognition as sr
import math

def scan_ambient_decibels():
    """
    SHARED UTILITY: Connects to default microphone hardware,
    samples room noise for 0.5s, and outputs raw decibels.
    """
    r = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            audio_data = r.record(source, duration=0.5)
            raw_bytes = audio_data.get_raw_data()
            if not raw_bytes:
                return 0.0
                
            samples = np.frombuffer(raw_bytes, dtype=np.int16)
            rms = np.sqrt(np.mean(samples.astype(np.float64)**2))
            
            if rms == 0:
                return 0.0
                
            return round(20 * math.log10(rms), 2)
        except Exception as e:
            print(f"[AUDIO UTILS ERROR] Global mic sample failed: {e}")
            return 45.0 # Safe baseline standard default fallback
