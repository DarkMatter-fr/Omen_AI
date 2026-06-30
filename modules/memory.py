"""
memory.py — Persistent Memory Subsystem for OMEN.

Two-tier architecture:
  1. Episodic Memory  (SQLite)   — Full turn-by-turn transcript per session.
                                   Written immediately after every exchange.
                                   Survives crashes; enables full session replay.

  2. Semantic Memory (ChromaDB)  — Vectorized session summaries.
                                   At session close, the session is summarised
                                   via Gemini and stored as a ChromaDB document.
                                   On each new query, top-K semantically similar
                                   past memories are retrieved and injected into
                                   the LLM context window automatically.

Public API
----------
    init_memory()                        → Call once at startup.
    new_session_id() -> str              → Generate and persist a fresh session UUID.
    current_session_id() -> str          → Return the active session UUID.
    store_turn(session_id, role, text)   → Persist one conversation turn to SQLite.
    get_session_turns(session_id) -> list→ Retrieve all turns for a session.
    semantic_recall(query, n=3) -> list  → Top-K relevant past memory snippets.
    commit_session_to_semantic(session_id, summary_fn) → Vectorise + store session.
    get_stats() -> dict                  → Counts for the UI status bar.
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

logger = logging.getLogger("OMEN.memory")

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_DB_PATH = _DATA_DIR / "memory.db"
_CHROMA_DIR = _DATA_DIR / "chroma"
_SESSION_FILE = _DATA_DIR / "current_session"

# ---------------------------------------------------------------------------
# INTERNAL STATE
# ---------------------------------------------------------------------------

_chroma_collection = None   # Lazy-initialised ChromaDB collection
_active_session_id: str = ""


# ---------------------------------------------------------------------------
# INITIALISATION
# ---------------------------------------------------------------------------

def init_memory() -> None:
    """
    Initialise the memory subsystem.
    Creates all required directories, the SQLite schema, and the ChromaDB
    collection. Safe to call multiple times (idempotent).
    """
    global _chroma_collection, _active_session_id

    # Ensure data directories exist
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    # --- SQLite Setup ---
    _init_sqlite()

    # --- ChromaDB Setup ---
    try:
        import chromadb
        chroma_client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
        _chroma_collection = chroma_client.get_or_create_collection(
            name="omen_semantic_memory",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"ChromaDB ready — collection 'omen_semantic_memory' "
            f"contains {_chroma_collection.count()} documents."
        )
    except Exception as e:
        logger.error(
            f"ChromaDB initialisation failed: {e}. "
            "Semantic recall will be disabled for this session."
        )
        _chroma_collection = None

    # --- Restore or create session ID ---
    if _SESSION_FILE.exists():
        _active_session_id = _SESSION_FILE.read_text(encoding="utf-8").strip()
        logger.info(f"Resumed session: {_active_session_id}")
    else:
        _active_session_id = new_session_id()

    logger.info("Memory subsystem initialised successfully.")


def _init_sqlite() -> None:
    """Create the episodic_memory table if it does not already exist."""
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session
            ON episodic_memory (session_id)
        """)
    logger.debug(f"SQLite ready at: {_DB_PATH}")


def _get_db() -> sqlite3.Connection:
    """Return a SQLite connection with WAL mode enabled for concurrency safety."""
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# SESSION MANAGEMENT
# ---------------------------------------------------------------------------

def new_session_id() -> str:
    """
    Generate a new UUID-based session ID, persist it to disk, and
    update the module-level active session tracker.

    Returns:
        The new session ID string.
    """
    global _active_session_id
    _active_session_id = str(uuid.uuid4())
    _SESSION_FILE.write_text(_active_session_id, encoding="utf-8")
    logger.info(f"New session started: {_active_session_id}")
    return _active_session_id


def current_session_id() -> str:
    """Return the currently active session ID."""
    return _active_session_id


# ---------------------------------------------------------------------------
# EPISODIC MEMORY (SQLite)
# ---------------------------------------------------------------------------

def store_turn(session_id: str, role: str, text: str) -> None:
    """
    Persist a single conversation turn to the episodic memory table.

    Args:
        session_id: The UUID of the current session.
        role:       'user' or 'model'.
        text:       The raw text content of the turn.
    """
    if not text or not text.strip():
        return

    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        with _get_db() as conn:
            conn.execute(
                "INSERT INTO episodic_memory (session_id, role, content, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (session_id, role, text.strip(), timestamp)
            )
        logger.debug(f"Stored [{role}] turn for session {session_id[:8]}…")
    except Exception as e:
        logger.error(f"Failed to write turn to SQLite: {e}")


def get_session_turns(session_id: str) -> list[dict]:
    """
    Retrieve all turns for a given session in chronological order.

    Args:
        session_id: The session UUID to query.

    Returns:
        List of dicts: [{"role": str, "content": str, "timestamp": str}, ...]
    """
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM episodic_memory "
                "WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            ).fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to read session turns from SQLite: {e}")
        return []


# ---------------------------------------------------------------------------
# SEMANTIC MEMORY (ChromaDB)
# ---------------------------------------------------------------------------

def semantic_recall(query: str, n_results: int = 3) -> list[str]:
    """
    Retrieve the top-K most semantically relevant past memory snippets.

    Runs a cosine similarity search against vectorized session summaries
    stored in ChromaDB. Returns an empty list if ChromaDB is unavailable
    or if fewer than 2 documents exist in the collection (not enough data).

    Args:
        query:     The current user prompt to match against.
        n_results: Number of top results to return (default: 3).

    Returns:
        List of relevant text snippets from past sessions.
    """
    if _chroma_collection is None:
        logger.debug("Semantic recall skipped — ChromaDB not available.")
        return []

    total_docs = _chroma_collection.count()
    if total_docs < 1:
        logger.debug("Semantic recall skipped — no memories stored yet.")
        return []

    # Clamp n_results to how many docs actually exist
    n_results = min(n_results, total_docs)

    try:
        results = _chroma_collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "distances"]
        )

        snippets = []
        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, dist in zip(docs, distances):
            # cosine distance: 0 = identical, 2 = opposite
            # Only include results that are meaningfully similar (dist < 1.2)
            if dist < 1.2 and doc:
                snippets.append(doc)
                logger.debug(f"Recalled memory (dist={dist:.3f}): {doc[:80]}…")

        return snippets

    except Exception as e:
        logger.error(f"ChromaDB semantic query failed: {e}")
        return []


def commit_session_to_semantic(session_id: str, summary_fn: Callable[[str], str]) -> None:
    """
    Summarise a completed session and store it in ChromaDB for future recall.

    Retrieves all turns for the session from SQLite, builds a raw transcript,
    calls `summary_fn` to generate a natural-language summary, then upserts
    it into the ChromaDB collection.

    Args:
        session_id:  The UUID of the session to commit.
        summary_fn:  A callable that takes a transcript string and returns
                     a summary string. Typically wraps a lightweight Gemini call.
    """
    if _chroma_collection is None:
        logger.warning("Cannot commit to semantic memory — ChromaDB unavailable.")
        return

    turns = get_session_turns(session_id)
    if len(turns) < 2:
        # Not enough content to bother summarising
        logger.debug(f"Session {session_id[:8]}… too short to commit to semantic memory.")
        return

    # Build a readable transcript
    transcript_lines = []
    for t in turns:
        speaker = "User" if t["role"] == "user" else "F.R.I.D.A.Y."
        transcript_lines.append(f"{speaker}: {t['content']}")
    transcript = "\n".join(transcript_lines)

    logger.info(f"Summarising session {session_id[:8]}… ({len(turns)} turns)")
    try:
        summary = summary_fn(transcript)
        if not summary or not summary.strip():
            logger.warning("Summary function returned empty result — skipping commit.")
            return

        # Upsert into ChromaDB (session_id as document ID ensures idempotency)
        _chroma_collection.upsert(
            ids=[session_id],
            documents=[summary],
            metadatas=[{
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "turn_count": str(len(turns))
            }]
        )
        logger.info(
            f"Session {session_id[:8]}… committed to semantic memory. "
            f"Summary: {summary[:120]}…"
        )
    except Exception as e:
        logger.error(f"Failed to commit session to semantic memory: {e}")


# ---------------------------------------------------------------------------
# STATS (for UI)
# ---------------------------------------------------------------------------

def get_stats() -> dict:
    """
    Return memory usage statistics for display in the UI status bar.

    Returns:
        dict with keys: total_turns, total_sessions, semantic_documents
    """
    stats = {
        "total_turns": 0,
        "total_sessions": 0,
        "semantic_documents": 0,
        "active_session_id": _active_session_id[:8] + "…" if _active_session_id else "none"
    }
    try:
        with _get_db() as conn:
            stats["total_turns"] = conn.execute(
                "SELECT COUNT(*) FROM episodic_memory"
            ).fetchone()[0]
            stats["total_sessions"] = conn.execute(
                "SELECT COUNT(DISTINCT session_id) FROM episodic_memory"
            ).fetchone()[0]
    except Exception as e:
        logger.error(f"Stats query failed: {e}")

    if _chroma_collection is not None:
        try:
            stats["semantic_documents"] = _chroma_collection.count()
        except Exception:
            pass

    return stats
