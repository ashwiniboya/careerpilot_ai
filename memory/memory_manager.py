"""
Memory Engine — three-tier memory for CareerPilot agents.

Tier 1  (session_memory)   : In-process dict, cleared at session end.
Tier 2  (episodic_memory)  : Persisted to SQLite `memories` table.
Tier 3  (semantic_memory)  : Summarised text embedded in ChromaDB for RAG retrieval.

Agents interact only with MemoryManager which coordinates all three tiers.
"""
from __future__ import annotations

import datetime
import json
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from database.models import Memory


# ---------------------------------------------------------------------------
# Tier 1 – Session Memory (in-process, ephemeral)
# ---------------------------------------------------------------------------

class SessionMemory:
    """Lightweight in-process key-value store scoped to one conversation turn."""

    def __init__(self):
        self._store: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def clear(self) -> None:
        self._store.clear()

    def all(self) -> Dict[str, Any]:
        return dict(self._store)


# ---------------------------------------------------------------------------
# Tier 2 – Episodic / Long-term SQL Memory
# ---------------------------------------------------------------------------

class EpisodicMemory:
    """Reads/writes structured key-value memories to the SQLite `memories` table."""

    def save(self, db: Session, user_id: int, memory_type: str, key: str, value: Any) -> None:
        """Upserts a memory record (updates if key exists, inserts otherwise)."""
        existing = (
            db.query(Memory)
            .filter(Memory.user_id == user_id, Memory.memory_type == memory_type, Memory.key == key)
            .first()
        )
        if existing:
            existing.val = value
            existing.updated_at = datetime.datetime.utcnow()
        else:
            db.add(Memory(user_id=user_id, memory_type=memory_type, key=key, val=value))
        db.commit()

    def load(self, db: Session, user_id: int, memory_type: Optional[str] = None) -> Dict[str, Any]:
        """Loads all memories for a user, optionally filtered by type."""
        q = db.query(Memory).filter(Memory.user_id == user_id)
        if memory_type:
            q = q.filter(Memory.memory_type == memory_type)
        rows = q.all()
        return {row.key: row.val for row in rows}

    def load_one(self, db: Session, user_id: int, memory_type: str, key: str) -> Optional[Any]:
        row = (
            db.query(Memory)
            .filter(Memory.user_id == user_id, Memory.memory_type == memory_type, Memory.key == key)
            .first()
        )
        return row.val if row else None

    def delete(self, db: Session, user_id: int, memory_type: str, key: str) -> None:
        db.query(Memory).filter(
            Memory.user_id == user_id, Memory.memory_type == memory_type, Memory.key == key
        ).delete()
        db.commit()


# ---------------------------------------------------------------------------
# Tier 3 – Semantic Memory (ChromaDB)
# ---------------------------------------------------------------------------

class SemanticMemory:
    """Stores and retrieves summarised conversation chunks via ChromaDB."""

    def __init__(self, vector_store=None):
        # vector_store is injected; allows None in unit tests (graceful degradation)
        self._vs = vector_store

    def embed_and_store(
        self, user_id: int, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if self._vs is None:
            logger.debug("SemanticMemory: vector_store not configured, skipping embed.")
            return
        meta = {"user_id": user_id, "doc_type": "memory", **(metadata or {})}
        self._vs.add_documents([text], [meta])
        logger.debug(f"SemanticMemory: stored chunk for user {user_id}.")

    def retrieve(
        self, user_id: int, query: str, limit: int = 3
    ) -> List[Dict[str, Any]]:
        if self._vs is None:
            return []
        return self._vs.search(query, user_id=user_id, doc_type="memory", limit=limit)


# ---------------------------------------------------------------------------
# MemoryManager – unified facade used by agents
# ---------------------------------------------------------------------------

class MemoryManager:
    """
    Single entry-point for all memory operations.

    Usage inside agents:
        mm = MemoryManager(db_session, user_id, vector_store)
        mm.session.set("last_resume_score", 82)
        mm.save_preference("work_setting", "Remote")
        ctx = mm.build_context(query="Tell me about my skills")
    """

    def __init__(self, db: Session, user_id: int, vector_store=None):
        self._db = db
        self._user_id = user_id
        self.session = SessionMemory()
        self._episodic = EpisodicMemory()
        self._semantic = SemanticMemory(vector_store)

    # ------------------------------------------------------------------
    # Preferences & Goals (structured long-term)
    # ------------------------------------------------------------------

    def save_preference(self, key: str, value: Any) -> None:
        self._episodic.save(self._db, self._user_id, "preference", key, value)

    def load_preferences(self) -> Dict[str, Any]:
        return self._episodic.load(self._db, self._user_id, "preference")

    def save_goal(self, key: str, value: Any) -> None:
        self._episodic.save(self._db, self._user_id, "goal", key, value)

    def load_goals(self) -> Dict[str, Any]:
        return self._episodic.load(self._db, self._user_id, "goal")

    # ------------------------------------------------------------------
    # Conversation / Interaction history
    # ------------------------------------------------------------------

    def append_interaction(self, role: str, content: str) -> None:
        """Appends one turn to conversation history stored in SQLite."""
        history = self._episodic.load_one(self._db, self._user_id, "short_term", "history") or []
        history.append({"role": role, "content": content, "ts": datetime.datetime.utcnow().isoformat()})
        # Keep last 20 turns to avoid unbounded growth
        if len(history) > 20:
            history = history[-20:]
        self._episodic.save(self._db, self._user_id, "short_term", "history", history)

    def load_history(self) -> List[Dict[str, Any]]:
        return self._episodic.load_one(self._db, self._user_id, "short_term", "history") or []

    # ------------------------------------------------------------------
    # Semantic retrieval
    # ------------------------------------------------------------------

    def store_summary(self, text: str, extra_meta: Optional[Dict] = None) -> None:
        self._semantic.embed_and_store(self._user_id, text, extra_meta)

    def retrieve_relevant_context(self, query: str) -> str:
        """Returns a concatenated string of top-k semantically relevant memories."""
        results = self._semantic.retrieve(self._user_id, query)
        if not results:
            return ""
        return "\n---\n".join(r["text"] for r in results)

    # ------------------------------------------------------------------
    # Context builder — constructs a rich context string for agent prompts
    # ------------------------------------------------------------------

    def build_context(self, query: str = "") -> str:
        """Assembles a structured context string from all memory tiers."""
        parts: List[str] = []

        prefs = self.load_preferences()
        if prefs:
            parts.append("## User Preferences\n" + json.dumps(prefs, indent=2))

        goals = self.load_goals()
        if goals:
            parts.append("## Career Goals\n" + json.dumps(goals, indent=2))

        history = self.load_history()
        if history:
            recent = history[-5:]  # last 5 turns for prompt brevity
            history_str = "\n".join(f"{h['role'].upper()}: {h['content']}" for h in recent)
            parts.append(f"## Recent Conversation\n{history_str}")

        if query:
            semantic_ctx = self.retrieve_relevant_context(query)
            if semantic_ctx:
                parts.append(f"## Relevant Past Context\n{semantic_ctx}")

        session_data = self.session.all()
        if session_data:
            parts.append("## Session Data\n" + json.dumps(session_data, indent=2))

        return "\n\n".join(parts) if parts else "No prior context available."
