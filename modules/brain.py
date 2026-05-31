import os
from dotenv import load_dotenv
from google import genai
from google.genai import types # We import the types library to build the template

load_dotenv()
client = genai.Client()

# --- 1. THE TEMPLATE (THE SCHEMA) ---
# We define the tool exactly as we mapped it out
software_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="open_software",
            description="Use this tool to launch a local desktop application or executable file on the Windows operating system.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "app_name": types.Schema(
                        type=types.Type.STRING,
                        description="The exact name of the application to open, such as 'Chrome', 'Spotify', or 'Discord'."
                    )
                },
                required=["app_name"],
            ),
        )
    ]
    
)

def generate_response(prompt):
    try:
        print(f"[BRAIN] Routing prompt to cloud cognition: '{prompt}'")
        
        system_instruction = (
            "You are OMEN, a highly advanced, slightly sarcastic AI assistant. "
            "Your input comes from voice-to-text software, so it may contain phonetic typos. "
            "If the user asks to open an application, you MUST use the open_software tool. "
            "Otherwise, answer conversationally in under 2 sentences."
        )
        
        # 2. HANDING THE TEMPLATE TO GEMINI
        # We add the 'tools' parameter to our config so the AI knows the menu exists
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                tools=[software_tool] # <--- Here is where we hand it the template
            )
        )
        
        # 3. CHECKING THE AI'S DECISION
        # Did the AI decide to use the tool, or did it just talk normally?
        if response.function_calls:
            # If it used the tool, we grab the payload and send it back to main.py
            function_call = response.function_calls[0]
            print(f"[BRAIN] Tool selected: {function_call.name}")
            return function_call
        else:
            # If it didn't use the tool, we just return the normal text
            print("[BRAIN] Neural synchronization complete. Text response acquired.")
            clean_text = response.text.replace("*", "")
            return clean_text
        
    except Exception as e:
        print(f"[BRAIN CRITICAL ERROR] Cloud connection severed: {e}")
        return "Sir, my cognitive link to the mainframe has been severed."