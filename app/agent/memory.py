"""In-memory conversation history, keyed by session_id."""
from collections import defaultdict
from typing import TypedDict


class MemoryEntry(TypedDict):
    role: str   # "user" | "assistant"
    content: str


_store: dict[str, list[MemoryEntry]] = defaultdict(list)


def get(session_id: str) -> list[MemoryEntry]:
    return list(_store[session_id])


def append(session_id: str, role: str, content: str) -> None:
    _store[session_id].append({"role": role, "content": content})


def clear(session_id: str) -> None:
    _store.pop(session_id, None)
