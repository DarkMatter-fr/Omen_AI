import os
from dotenv import load_dotenv
from google import genai

# 1. Load the hidden environment variables from your .env file
load_dotenv()

# 2. Initialize the AI Client
# The SDK automatically detects the GEMINI_API_KEY saved in your .env file
client = genai.Client()

def generate_response(prompt):
    """
    COGNITIVE ENGINE: Packages the user's transcribed voice text, 
    sends it to the Gemini neural network, and extracts the text reply.
    """
    try:
        print(f"[BRAIN] Routing prompt to cloud cognition: '{prompt}'")
        
        # 3. System Instruction to shape OMEN's persona and handle phonetic speech errors
        system_instruction = (
            "You are OMEN, a highly advanced, slightly sarcastic AI assistant. "
            "Your input comes from voice-to-text software, so it may contain phonetic typos "
            "(e.g., 'oh man' or 'amen' instead of 'OMEN'). Ignore these transcription errors, "
            "understand the user's intent, and answer as OMEN. Keep responses under 2 sentences."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        
        print("[BRAIN] Neural synchronization complete. Response acquired.")
        
        # Clean up any markdown formatting symbols so the voice synthesizer doesn't read them out loud
        clean_text = response.text.replace("*", "")
        return clean_text
        
    except Exception as e:
        print(f"[BRAIN CRITICAL ERROR] Cloud connection severed: {e}")
        return "Sir, my cognitive link to the mainframe has been severed. Please check my API credentials."