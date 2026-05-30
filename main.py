import os
import eel
import time
import modules
from modules import mouth as mouth
from modules import ears as ear


#Resolve file architecture pathways
current_dir = os.path.dirname(os.path.realpath(__file__))
web_dir = os.path.join(current_dir, 'web')
eel.init(web_dir)

@eel.expose
def process_voice_input():
    """
    Exposed JS link. Triggers your physical microphone capture pipeline,
    manages UI state animations, and handles text-to-speech output safely.
    """
    # 1. Update UI state to Crimson listening mode
    print("[OMEN SYS] Shifting interface parameters to: LISTENING")
    eel.setAssistantState('listening')()
    
    # 2. Fire the hardware signal processing loop (Ears handles decibels internally)
    query = ear.take_command()
    
    # 3. Guard pattern: If audio capture failed or room was silent
    if query == "none":
        print("[OMEN SYS] Pipeline returned empty wave buffer. Resetting.")
        eel.setAssistantState('idle')()
        return

    # 4. Append user's recognized text directly into your glass panel
    eel.addMessage('user', query)()

    # 5. Intercept local meme phrases instantly before cloud routing
    if "is this tuff" in query:
        print("[OMEN SYS] Direct local match for structural meme trigger.")
        eel.triggerTuffMode(5000)() # Spins orange phantom fire for 5 seconds
        
        response = "Sir, the level of structural tuffness detected in this module is critical. Extremely tuff."
        
        # Output text to UI
        eel.addMessage('assistant', response)()
        
        # Trigger asynchronous physical voice output
        mouth.speak(response)
        
    else:
        # 6. Shift UI state to Violet rotating thinking ring
        print("[OMEN SYS] Routing prompt sequence to cognition engines...")
        eel.setAssistantState('thinking')()
        
        # Temporary core placeholder loop before we bind modules/brain.py
        time.sleep(2.5) 
        
        fallback_response = "System core synchronization active. Cognition engine online, awaiting API binding block."
        
        # Output text to UI
        eel.addMessage('assistant', fallback_response)()
        
        # Trigger asynchronous physical voice output
        mouth.speak(fallback_response)
        
    # Note: The 'idle' reset state is now handled inside mouth.py 
    # to ensure the UI stays active while OMEN is speaking.

# Initialize the UI viewport layout window
print("[OMEN CORE] Launching interface dashboard container...")
eel.start('index.html', size=(1000, 700))