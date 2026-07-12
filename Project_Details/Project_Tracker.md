# OMEN OS — Project Tracker

## Current Milestone: M4 — Modern Chat UI ✅

---

## Milestone Log

### ✅ Milestone 0 — Foundation Stabilization (COMPLETE)

| # | Task | Status |
|---|---|---|
| 1 | Fix double-speak bug in `mouth.py` | ✅ Done |
| 2 | Fix alias replacement scope bug in `ears.py` | ✅ Done |
| 3 | Remove dead `from ast import alias` import | ✅ Done |
| 4 | Move `.env` to project root | ✅ Done |
| 5 | Update `brain.py` env path resolution | ✅ Done |
| 6 | Add `requirements.txt` | ✅ Done |
| 7 | Update `.gitignore` | ✅ Done |
| 8 | Add conversation memory (multi-turn history) | ✅ Done |
| 9 | Fix XSS in `script.js` terminal logger | ✅ Done |
| 10 | Add Python `logging` module across all modules | ✅ Done |
| 11 | Add text input fallback in UI | ✅ Done |
| 12 | Add keyboard shortcut (Enter to send) | ✅ Done |
| 13 | Add clear session button | ✅ Done |
| 14 | Color-coded terminal log lines | ✅ Done |
| 15 | Populate all planning docs | ✅ Done |

---

### ✅ Milestone 1 — Conversational Memory (COMPLETE)
Persistent SQLite + ChromaDB semantic memory system.

| # | Task | Status |
|---|---|---|
| 1 | Install `chromadb` dependency | ✅ Done |
| 2 | Create `modules/memory.py` (SQLite + ChromaDB subsystem) | ✅ Done |
| 3 | Integrate memory into `modules/brain.py` | ✅ Done |
| 4 | Call `memory.init_memory()` in `main.py` on startup | ✅ Done |
| 5 | Expose `get_memory_stats()` Eel endpoint | ✅ Done |
| 6 | Update `requirements.txt` | ✅ Done |
| 7 | Update `.gitignore` (exclude `data/`) | ✅ Done |
| 8 | Verify: init, write, recall pipeline | ✅ Done |


### ✅ Milestone 2 — Wake Word + Continuous Listening (COMPLETE)
OpenWakeWord (ONNX) — always-on hands-free activation via `"hey_jarvis"` (custom `hey_omen.onnx` auto-loaded if present in `data/models/`).

| # | Task | Status |
|---|---|---|
| 1 | Install `openwakeword>=0.6.0` dependency | ✅ Done |
| 2 | Create `modules/wake_word.py` (WakeWordListener daemon thread) | ✅ Done |
| 3 | Integrate `_wake_event` + `_is_processing` threading events in `main.py` | ✅ Done |
| 4 | Add `_wake_word_poll_loop()` daemon thread in `main.py` | ✅ Done |
| 5 | Set `_is_processing` flag in `_process_query()` to suppress re-triggering | ✅ Done |
| 6 | Expose `toggle_wake_word()` Eel endpoint | ✅ Done |
| 7 | Expose `get_wake_word_status()` Eel endpoint | ✅ Done |
| 8 | Add wake word status pill + toggle button to `web/index.html` | ✅ Done |
| 9 | Add wake word telemetry row to sidebar | ✅ Done |
| 10 | Add pill CSS + state animations to `web/style.css` | ✅ Done |
| 11 | Add `updateWakeWordStatus()` + `toggleWakeWord()` to `web/script.js` | ✅ Done |
| 12 | Update `requirements.txt` | ✅ Done |

### ✅ Milestone 3 — Voice Quality Upgrade (COMPLETE)
edge-tts (Microsoft Neural) — replaces pyttsx3 robotic SAPI voice. Auto-falls back to pyttsx3 if offline.

| # | Task | Status |
|---|---|---|
| 1 | Install `edge-tts>=6.1.12` dependency | ✅ Done |
| 2 | Install `playsound==1.2.2` dependency | ✅ Done |
| 3 | Rewrite `modules/mouth.py` — edge-tts primary, pyttsx3 fallback | ✅ Done |
| 4 | Add `.env` config support (`EDGE_TTS_VOICE`, `EDGE_TTS_RATE`) | ✅ Done |
| 5 | Update `requirements.txt` | ✅ Done |
| 6 | Verify standalone `speak()` test | ✅ Done |

### ✅ Milestone 4 — Modern Chat UI (COMPLETE)
Chat bubbles, streaming typewriter text, waveform visualizer, molten amber/gold HUD aesthetic matching reference image.

| # | Task | Status |
|---|---|---|
| 1 | Implement chat bubble layout (user/OMEN sided) | ✅ Done |
| 2 | Streaming typewriter text effect | ✅ Done |
| 3 | Canvas orb visualizer (idle/listening/thinking states) | ✅ Done |
| 4 | Thinking dots animation bubble | ✅ Done |
| 5 | Rewrite `style.css` — Orbitron font, vignette, CRT scanlines, dark void aesthetic | ✅ Done |
| 6 | Enhanced orb render — 8-wisp particle crackle, 6-layer thinking arcs, audio-reactive EQ | ✅ Done |
| 7 | HUD corner brackets with tick marks | ✅ Done |
| 8 | Orb state label (IDLE / LISTENING / PROCESSING) | ✅ Done |
| 9 | Welcome divider + Orbitron display font on logo | ✅ Done |

### 🔲 Milestone 5 — Computer Control Suite
Window management, screenshots, OCR, Playwright automation.

### 🔲 Milestone 6 — Multi-LLM Router
Route by task: Flash → Pro → Local (Ollama fallback).

### 🔲 Milestone 7 — Knowledge Base + RAG
Ingest PDFs, docs, code. Semantic retrieval into context.

### 🔲 Milestone 8 — Real Web Search
Replace stub with Serper/Brave API + web reader.

### 🔲 Milestone 9 — Planning + Task Engine
Tasks, reminders, goals, calendar integration.

### 🔲 Milestone 10 — Multi-Agent Orchestration
Planner, Researcher, Coder, Critic, Memory Manager agents.

### 🔲 Milestone 11 — Plugin Architecture
Dynamic loading, sandboxing, permissions, marketplace-ready.

### 🔲 Milestone 12 — Security Hardening
Vault, approval dialogs, audit log, rate limiting.

### 🔲 Milestone 13 — Observability
Structured logs, metrics, error dashboard, profiling.
