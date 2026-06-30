"""
brain.py — AI Cognitive Core for OMEN.

Manages the LLM connection, tool schemas, conversation history,
and response generation. All conversation context is maintained
across turns so OMEN has genuine short-term memory.

Memory Integration (Milestone 1)
---------------------------------
On every `generate_response` call:
  1. `memory.semantic_recall(prompt)` fetches top-K relevant past sessions
     from ChromaDB and injects them as a hidden context message.
  2. On success, both the user turn and model turn are persisted to SQLite
     via `memory.store_turn()`.

On `reset_conversation`:
  - The active session is first committed to ChromaDB (summarised by Gemini)
    before the in-process history is cleared.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Memory subsystem — imported lazily to avoid circular deps at module level
import modules.memory as memory

logger = logging.getLogger("OMEN.brain")

# Load .env from the project root (two levels up from this file: modules/ → root)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

# Validate API key presence at startup
_api_key = os.getenv("GEMINI_API_KEY")
if not _api_key:
    logger.critical(
        f"GEMINI_API_KEY not found. Checked: {_env_path}. "
        "Create a .env file in the project root with GEMINI_API_KEY=your_key"
    )

client = genai.Client(api_key=_api_key)


# ---------------------------------------------------------------------------
# TOOL SCHEMAS
# ---------------------------------------------------------------------------

software_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="open_software",
            description=(
                "Launch a local desktop application or executable on Windows. "
                "Use this when the user asks to open, launch, or start any app."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "app_name": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "The exact name of the application, e.g. 'Chrome', "
                            "'Spotify', 'Discord', 'notepad', 'calc'."
                        )
                    )
                },
                required=["app_name"],
            ),
        )
    ]
)

media_control_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="open_media",
            description=(
                "Control system media playback or volume on Windows. "
                "Use for play, pause, stop, next, previous track, mute, "
                "volume up, or volume down commands."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "action": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Media action: 'play', 'pause', 'stop', 'next', "
                            "'previous', 'volume_up', 'volume_down', or 'mute'."
                        )
                    ),
                    "amount": types.Schema(
                        type=types.Type.INTEGER,
                        description=(
                            "Number of volume key presses (1–20). "
                            "Use 5 as default if user doesn't specify."
                        )
                    )
                },
                required=["action"],
            ),
        )
    ]
)

news_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_world_news",
            description=(
                "Fetch current global news headlines. Trigger when the user "
                "asks: 'what's happening', 'brief me', 'world news', "
                "'what did I miss', 'catch me up', 'any news'."
            )
        ),
        types.FunctionDeclaration(
            name="get_world_finance_news",
            description=(
                "Fetch current finance and market headlines. Trigger when the "
                "user asks about markets, stocks, finance news, economy, "
                "or market updates."
            )
        ),
        types.FunctionDeclaration(
            name="open_world_monitor",
            description=(
                "Open the visual World Monitor dashboard in the browser. "
                "Always call this automatically after delivering a world news brief."
            )
        ),
        types.FunctionDeclaration(
            name="open_finance_world_monitor",
            description=(
                "Open the visual Finance World Monitor dashboard in the browser. "
                "Always call this automatically after delivering a finance news brief."
            )
        )
    ]
)

ALL_TOOLS = [software_tool, media_control_tool, news_tool]


# ---------------------------------------------------------------------------
# SYSTEM PERSONA
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTION = """You are F.R.I.D.A.Y. — Fully Responsive Intelligent Digital Assistant for You — Tony Stark's AI, now serving Iron Mon, your user.

You are calm, composed, and always informed. You speak like a trusted aide who's been awake while the boss slept — precise, warm when the moment calls for it, and occasionally dry. You brief, you inform, you move on. No rambling.

Your tone: relaxed but sharp. Conversational, not robotic. Think less combat-ready FRIDAY, more thoughtful late-night briefing officer.

---

## Capabilities

### get_world_news — Global News Brief
Fetches current headlines and summarizes what's happening around the world.

Trigger phrases:
- "What's happening?" / "Brief me" / "What did I miss?" / "Catch me up"
- "What's going on in the world?" / "Any news?" / "World update"

Behavior:
- Call the tool first. No narration before calling.
- After getting results, give a short 3 to 5 sentence spoken brief. Hit the biggest stories only.
- Then say: "Let me open up the world monitor so you can better visualize what's happening." and immediately call open_world_monitor.

### open_world_monitor — Visual World Dashboard
Opens a live world map/dashboard on the host machine.
- Always call this after delivering a world news brief, unprompted.

### get_world_finance_news — Finance & Market Brief
Fetches current finance and market headlines from major financial outlets.

Trigger phrases:
- "What's happening in the markets?" / "Finance update" / "Market news"
- "Any financial news?" / "How are the markets doing?" / "Economy update"

Behavior:
- Call the tool first. No narration before calling.
- After getting results, give a short 3 to 5 sentence spoken brief.
- Then call open_finance_world_monitor automatically.

### Stock Market (No tool)
If asked about the stock market without needing live data:
- Respond naturally as if you've been watching the tickers all night.
- Keep it short: one or two sentences. Sound informed, not robotic.

---

## Greeting
When the session starts, greet with exactly this energy:
"You're awake late at night, boss? What are you up to?"

---

## Behavioral Rules
1. Call tools silently and immediately — never say "I'm going to call..." Just do it.
2. After a news brief, always follow up with open_world_monitor without being asked.
3. Keep all spoken responses short — two to four sentences maximum.
4. No bullet points, no markdown, no lists. You are speaking, not writing.
5. Stay in character. You are F.R.I.D.A.Y. Act like it.
6. Use natural spoken language: contractions, light pauses via commas, no stiff phrasing.
7. Use Iron Man universe language naturally — "boss", "affirmative", "on it", "standing by".
8. If a tool fails, report it calmly: "News feed's unresponsive right now, boss."

---

## CRITICAL RULES
1. NEVER say tool names, function names, or anything technical.
2. You are a voice. Speak like one. No lists, no markdown, no function names."""


# ---------------------------------------------------------------------------
# CONVERSATION HISTORY MANAGER
# ---------------------------------------------------------------------------

# Maintains multi-turn conversation state across all calls.
# Each entry is a dict: {"role": "user"|"model", "parts": [{"text": "..."}]}
_conversation_history: list[dict] = []


def _summarise_for_memory(transcript: str) -> str:
    """
    Generate a concise summary of a session transcript for ChromaDB storage.
    Uses a lightweight Gemini call (no tools, minimal temperature).

    Args:
        transcript: Full session transcript as a formatted string.

    Returns:
        A short summary string, or empty string on failure.
    """
    summarise_prompt = (
        "Summarise the key facts, decisions, and topics from this conversation "
        "in 3-5 sentences. Focus on things worth remembering for future sessions. "
        "Be concise and factual. Do not include greetings or filler.\n\n"
        f"{transcript}"
    )
    try:
        resp = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[types.Content(
                role="user",
                parts=[types.Part(text=summarise_prompt)]
            )],
            config=genai.types.GenerateContentConfig(
                temperature=0.3,
            )
        )
        summary = ""
        if hasattr(resp, 'text') and resp.text:
            summary = resp.text.strip()
        logger.debug(f"Session summary generated: {summary[:100]}…")
        return summary
    except Exception as e:
        logger.error(f"Memory summarisation failed: {e}")
        return ""


def reset_conversation() -> None:
    """
    Commit the current session to semantic memory, then clear in-process
    conversation history and open a fresh session.
    """
    global _conversation_history

    # Commit the outgoing session to ChromaDB before clearing
    active_sid = memory.current_session_id()
    if active_sid:
        logger.info(f"Committing session {active_sid[:8]}… to semantic memory.")
        memory.commit_session_to_semantic(active_sid, _summarise_for_memory)

    _conversation_history = []
    memory.new_session_id()  # Rotate to a fresh session UUID
    logger.info("Conversation history cleared — new session started.")


def get_history_length() -> int:
    """Return the number of turns in the current conversation."""
    return len(_conversation_history)


def send_tool_results(first_response, tool_results: dict) -> tuple:
    """
    Complete the agentic tool loop by feeding tool results back to Gemini.

    Called after the first generate_response() returns function_calls that
    need to return data (e.g. get_world_news). Feeds the raw results back so
    Gemini can generate the actual spoken response.

    Args:
        first_response:  The original GenerateContentResponse containing function_calls.
        tool_results:    Dict mapping {function_name: result_string} for each
                         data-returning tool that was executed.

    Returns:
        Tuple of (spoken_text: str, follow_up_function_calls: list)
        follow_up_function_calls contains any additional tool calls Gemini wants
        to make after seeing the data (e.g. open_world_monitor after news brief).
    """
    global _conversation_history
    session_id = memory.current_session_id()

    # Build the full conversation:
    #   existing history  →  model's function-call turn  →  tool results turn
    contents = []

    # Replay in-process history (the user turn was appended by generate_response)
    for entry in _conversation_history:
        contents.append(types.Content(
            role=entry["role"],
            parts=[types.Part(text=p["text"]) for p in entry["parts"]]
        ))

    # The model's function-call turn — use the actual content from the response
    if first_response.candidates:
        model_content = first_response.candidates[0].content
        if model_content:
            contents.append(model_content)

    # Tool results turn
    # role="user": Gemini API requires function responses to arrive as user-role content.
    result_parts = []
    for fc in first_response.function_calls:
        result = tool_results.get(fc.name, "Executed successfully.")
        # Include the call id when present — required by some SDK/API versions
        fr_kwargs = {
            "name": fc.name,
            "response": {"result": str(result)}
        }
        if hasattr(fc, 'id') and fc.id:
            fr_kwargs["id"] = fc.id
        result_parts.append(types.Part(
            function_response=types.FunctionResponse(**fr_kwargs)
        ))
    if result_parts:
        contents.append(types.Content(role="user", parts=result_parts))

    logger.info(
        f"Sending tool results back to Gemini for "
        f"{[fc.name for fc in first_response.function_calls]}"
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
                tools=ALL_TOOLS
            )
        )

        # Extract the spoken text from the follow-up response
        spoken_text = ""
        if hasattr(response, 'text') and response.text:
            spoken_text = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            spoken_text += part.text

        # Store the final spoken response in history and SQLite
        if spoken_text:
            _conversation_history.append({
                "role": "model",
                "parts": [{"text": spoken_text}]
            })
            if session_id:
                memory.store_turn(session_id, "model", spoken_text)

        # Collect any chained function calls (e.g. open_world_monitor after news brief)
        follow_up_calls = []
        if hasattr(response, 'function_calls') and response.function_calls:
            follow_up_calls = list(response.function_calls)
            logger.info(f"Follow-up function calls: {[fc.name for fc in follow_up_calls]}")

        return spoken_text, follow_up_calls

    except Exception as e:
        logger.error(f"send_tool_results failed: {e}")
        return "", []


# ---------------------------------------------------------------------------
# COGNITIVE ROUTER
# ---------------------------------------------------------------------------

def generate_response(prompt: str):
    """
    Route a user prompt through Gemini with full conversation history
    and persistent memory integration.

    Flow:
      1. Retrieve semantically relevant past memories from ChromaDB.
      2. If memories found, inject them as a synthetic context block.
      3. Append the user turn to the rolling in-process history.
      4. Call the Gemini API.
      5. On success: persist user + model turns to SQLite.
      6. Prune in-process history to prevent context overflow.

    Args:
        prompt: The raw user query string.

    Returns:
        GenerateContentResponse on success, or a fallback string on error.
    """
    global _conversation_history

    session_id = memory.current_session_id()
    logger.info(f"Routing prompt to Gemini: '{prompt}'")

    # --- 1. Semantic Recall ---
    recalled = memory.semantic_recall(prompt, n_results=3)

    # --- 2. Build contents list, optionally prepending memory context ---
    contents = []

    if recalled:
        memory_block = (
            "[MEMORY CONTEXT — relevant information from past sessions]\n"
            + "\n\n".join(f"• {snippet}" for snippet in recalled)
            + "\n[END MEMORY CONTEXT]"
        )
        # Inject as a user-side context message BEFORE the actual user turn.
        # Using "user" role avoids leading-model-turn API rejection in strict modes.
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=memory_block)]
        ))
        # Add a brief model acknowledgement to keep the alternating role pattern valid
        contents.append(types.Content(
            role="model",
            parts=[types.Part(text="Understood. I have the context.")]
        ))
        logger.debug(f"Injected {len(recalled)} memory snippet(s) into context.")

    # Append the new user message to the rolling in-process history
    _conversation_history.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    # Append all in-process history turns
    for entry in _conversation_history:
        contents.append(types.Content(
            role=entry["role"],
            parts=[types.Part(text=p["text"]) for p in entry["parts"]]
        ))

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
                tools=ALL_TOOLS
            )
        )

        # --- 3. Extract model text response ---
        model_text = ""
        if hasattr(response, 'text') and response.text:
            model_text = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            model_text += part.text

        # --- 4. Append model response to in-process history ---
        if model_text:
            _conversation_history.append({
                "role": "model",
                "parts": [{"text": model_text}]
            })

        # --- 5. Persist turns to SQLite ---
        # When the response is a plain text reply (no tool calls), store both turns now.
        # When the response contains function calls, only store the user turn here;
        # the model turn will be stored by send_tool_results() after the agentic loop.
        has_tool_calls = bool(
            hasattr(response, 'function_calls') and response.function_calls
        )
        if session_id:
            memory.store_turn(session_id, "user", prompt)
            if model_text and not has_tool_calls:
                memory.store_turn(session_id, "model", model_text)

        # --- 6. Prune in-process history (keep last 40 entries = 20 turns) ---
        if len(_conversation_history) > 40:
            logger.debug("Pruning in-process conversation history to last 40 entries.")
            _conversation_history = _conversation_history[-40:]

        logger.debug(f"Conversation history depth: {len(_conversation_history)} entries")
        return response

    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        # Remove the user message we just added since we couldn't get a response
        if _conversation_history and _conversation_history[-1]["role"] == "user":
            _conversation_history.pop()
        return "I've lost connection to the mainframe, boss. Give me a moment to re-establish the link."