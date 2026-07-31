"""
Hermes Agent Memory – Short-term (in-memory) + Long-term (SQLite)
"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    key: str
    value: Any
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    ttl: float | None = None  # seconds; None = permanent

    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "tags": self.tags,
            "created_at": self.created_at,
            "ttl": self.ttl,
        }


class ShortTermMemory:
    """Fast in-memory key-value store with optional TTL."""

    def __init__(self, max_size: int = 1000):
        self._store: dict[str, MemoryEntry] = {}
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any, ttl: float | None = None, tags: list[str] | None = None) -> None:
        async with self._lock:
            if len(self._store) >= self._max_size:
                # Evict oldest entry
                oldest = min(self._store.values(), key=lambda e: e.created_at)
                del self._store[oldest.key]

            self._store[key] = MemoryEntry(key=key, value=value, tags=tags or [], ttl=ttl)

    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return default
            if entry.is_expired:
                del self._store[key]
                return default
            return entry.value

    async def delete(self, key: str) -> bool:
        async with self._lock:
            return self._store.pop(key, None) is not None

    async def search_by_tag(self, tag: str) -> list[MemoryEntry]:
        async with self._lock:
            return [e for e in self._store.values() if tag in e.tags and not e.is_expired]

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def cleanup_expired(self) -> int:
        async with self._lock:
            expired = [k for k, v in self._store.items() if v.is_expired]
            for k in expired:
                del self._store[k]
            return len(expired)

    def __len__(self) -> int:
        return len(self._store)

    def snapshot(self) -> list[dict]:
        return [v.to_dict() for v in self._store.values() if not v.is_expired]


class ConversationMemory:
    """Stores a conversation history (list of messages) per session."""

    def __init__(self, max_messages: int = 100):
        self._sessions: dict[str, list[dict]] = {}
        self._max_messages = max_messages

    def add_message(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        messages = self._sessions[session_id]
        messages.append({"role": role, "content": content})
        if len(messages) > self._max_messages:
            messages.pop(0)

    def get_history(self, session_id: str) -> list[dict]:
        return self._sessions.get(session_id, []).copy()

    def clear_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())


class AgentMemory:
    """Unified memory interface for a Hermes agent."""

    def __init__(self, agent_id: str, ttl: float = 3600):
        self.agent_id = agent_id
        self.default_ttl = ttl
        self.short_term = ShortTermMemory()
        self.conversation = ConversationMemory()
        self._facts: list[str] = []  # Long-term accumulated facts

    # ── Short-term ─────────────────────────────────────────────
    async def remember(self, key: str, value: Any, ttl: float | None = None) -> None:
        await self.short_term.set(key, value, ttl=ttl or self.default_ttl)

    async def recall(self, key: str, default: Any = None) -> Any:
        return await self.short_term.get(key, default)

    async def forget(self, key: str) -> bool:
        return await self.short_term.delete(key)

    # ── Conversation ───────────────────────────────────────────
    def add_user_message(self, content: str, session: str = "default") -> None:
        self.conversation.add_message(session, "user", content)

    def add_assistant_message(self, content: str, session: str = "default") -> None:
        self.conversation.add_message(session, "assistant", content)

    def get_conversation(self, session: str = "default") -> list[dict]:
        return self.conversation.get_history(session)

    # ── Facts ──────────────────────────────────────────────────
    def learn_fact(self, fact: str) -> None:
        if fact not in self._facts:
            self._facts.append(fact)

    def get_facts(self) -> list[str]:
        return self._facts.copy()

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "short_term_count": len(self.short_term),
            "facts_count": len(self._facts),
            "facts": self._facts,
            "short_term_snapshot": self.short_term.snapshot(),
        }
