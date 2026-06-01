import os
import eel
import subprocess
from modules.ears import take_command
from modules.mouth import speak
from modules.brain import generate_response

# Initialize the UI framework
current_dir = os.path.dirname(os.path.realpath(__file__))
web_dir = os.path.join(current_dir, 'web')
eel.init(web_dir)

@eel.expose
def process_voice_input():
    eel.setAssistantState('listening')()
    
    # 1. Listen for the user's voice
    query = take_command()
    
    if query == "none":
        eel.setAssistantState('idle')()
        return

    # Update UI with user's text
    eel.addMessage('user', query)()

    # Easter Egg check
    if "is this tuff" in query:
        eel.triggerTuffMode(5000)() 
        response = "Sir, the level of structural tuffness detected is critical. Extremely tuff."
        eel.addMessage('assistant', response)()
        speak(response)
        
    else:
        eel.setAssistantState('thinking')()
        
        # 2. Send the voice text to Gemini and wait for the response
        response = generate_response(query)
        
        # 3. THE ORCHESTRATION LAYER (Function Calling Interception)
        # We check if the response has a 'name' attribute, meaning it is a tool payload, not text.
        if hasattr(response, "name") and response.name == "open_software":
            
            # Extract the specific app name from the AI's data packet
            target_app = response.args["app_name"]
            print(f"[SYSTEM] AI requested to launch: {target_app}")
            
            try:
                # Tell Windows to execute the application
                # The 'start' command opens software via the Windows command line
                subprocess.run(["start", target_app], shell=True)
                
                # Create a success message
                success_text = f"Initializing {target_app} now, sir."
                print(f"[SYSTEM] Successfully launched {target_app}")
                
                # Update UI and speak
                eel.addMessage('assistant', success_text)()
                speak(success_text)
                
            except Exception as e:
                error_text = "Sir, I encountered an error while trying to launch the application."
                print(f"[SYSTEM ERROR] Could not launch {target_app}: {e}")
                eel.addMessage('assistant', error_text)()
                speak(error_text)
                
        else:
            # 4. NORMAL CONVERSATION ROUTE
            # If the response doesn't have a 'name' attribute, it's just normal AI text.
            eel.addMessage('assistant', response)()
            speak(response)

print("[OMEN MAIN] Orchestration layer active. Launching UI framework...")
eel.start('index.html', size=(1000, 700))