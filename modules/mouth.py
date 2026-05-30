import pyttsx3
import time

def speak(audio):
    print(f"Omen: {audio}")
    # Initialize inside the function to avoid thread-locking
    engine = pyttsx3.init()
    
    # Optional: Set voice properties
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[0].id) 
    engine.setProperty('rate', 200)

    
    print("--- DEBUG: Audio Engine Start ---")
    engine.say(audio)
    engine.runAndWait()
    print("--- DEBUG: Audio Engine Finished ---")

    engine.say(audio)
    engine.runAndWait()
    
    # Mandatory cleanup to release the audio driver
    engine.stop()
    time.sleep(0.1)


def clean_slang(text):
    # Map common mishearings to your desired meme words
    slang_map = {
        "tough": "tuff",
        "top": "tuff",
        "stuff": "tuff"
    }
    
    words = text.split()
    # Replace words if they exist in our map
    cleaned_words = [slang_map.get(w, w) for w in words]
    return " ".join(cleaned_words)

# Update your take_command function:
# query = r.recognize_google(audio, language='en-in')
# return clean_slang(query.lower())