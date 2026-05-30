import speech_recognition as sr
try:
    from modules import audio_utils as au
except ModuleNotFoundError:
    import audio_utils as au

def take_command():
    """
    Main sensory entry point. Scans the environment room decibels, 
    configures its thresholds automatically, and transcribes voice input.
    """
    r = sr.Recognizer()
    
    # 1. Check the room volume using your shared utility
    db_level = au.scan_ambient_decibels()
    print(f"[EARS] Global utility tracking layer reports: {db_level} dB")
    
    # 2. Map raw decibel value directly to threshold parameters
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

    print(f"[EARS] Matrix calibrated into: {detected_mode.upper()} ({r.energy_threshold} energy cutoff)")

    # 3. Open the hardware microphone and listen
    with sr.Microphone() as source:
        try:
            # Enforce a maximum recording ceiling of 15 seconds to prevent memory bloat
            audio = r.listen(source, timeout=4, phrase_time_limit=15)
            print("[EARS] Sound wave captured. Transcribing language frequencies...")
            
            # Use English-India language tagging to extract syllables accurately
            query = r.recognize_google(audio, language='en-in').lower()
            
            # Local normalization rule
            if "tough" in query:
                query = query.replace("tough", "tuff")
                
            return query
            
        except sr.WaitTimeoutError:
            print("[EARS] Aborted: User did not speak within time window.")
            return "none"
        except sr.UnknownValueError:
            print("[EARS] Unresolved: Sound wave structural format unreadable.")
            return "none"
        except Exception as e:
            print(f"[EARS CRITICAL ERROR] Pipeline shattered: {e}")
            return "none"