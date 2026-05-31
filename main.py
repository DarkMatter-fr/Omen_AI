import os
import eel
from modules.ears import take_command
from modules.mouth import speak
from modules.brain import generate_response

current_dir = os.path.dirname(os.path.realpath(__file__))
web_dir = os.path.join(current_dir, 'web')
eel.init(web_dir)

@eel.expose
def process_voice_input():
    eel.setAssistantState('listening')()
    
    query = take_command()
    
    if query == "none":
        eel.setAssistantState('idle')()
        return

    eel.addMessage('user', query)()

    if "is this tuff" in query:
        eel.triggerTuffMode(5000)() 
        response = "Sir, the level of structural tuffness detected is critical. Extremely tuff."
        eel.addMessage('assistant', response)()
        speak(response)
        
    else:
        eel.setAssistantState('thinking')()
        ai_response = generate_response(query)
        eel.addMessage('assistant', ai_response)()
        speak(ai_response)

print("[OMEN MAIN] Orchestration layer active. Launching UI framework...")
eel.start('index.html', size=(1000, 700))