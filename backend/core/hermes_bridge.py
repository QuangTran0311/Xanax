"""
Hermes bridge for Xanax UI.

This module keeps only the thin UI-facing pieces:
- local session tracking for the chat UI
- an OpenAI-compatible client for Hermes-configured local/remote models

Xanax does not own a separate chat backend.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import AsyncIterator
from uuid import uuid4

import httpx
from dotenv import dotenv_values

from core.hermes_paths import hermes_home
from hub.config import settings

logger = logging.getLogger("xanax.hermes_bridge")


@dataclass
class ChatSession:
    session_id: str
    title: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "id": self.session_id,
            "title": self.title,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.created_at)),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.updated_at)),
            "message_count": len(self.messages),
        }


class HermesBridge:
    """Thin chat client + in-memory session store."""

    def __init__(self):
        self._sessions: dict[str, ChatSession] = {}
        self._lock = asyncio.Lock()
        self.base_url, self.model, self.api_key = self._resolve_chat_config()
        self._headers = self._build_headers(self.api_key)

    def _resolve_chat_config(self) -> tuple[str, str, str]:
        """
        Resolve chat backend settings.

        Priority:
        1. Xanax HUB_LLM_* env vars
        2. Hermes local config from the platform-specific Hermes home
        3. Project defaults
        """
        base_url = settings.llm_api_base.rstrip("/")
        model = settings.llm_model
        api_key = settings.llm_api_key

        hermes_root = hermes_home()
        hermes_env = hermes_root / ".env" if hermes_root is not None else None
        hermes_config = hermes_root / "config.yaml" if hermes_root is not None else None

        fallback_env = dotenv_values(hermes_env) if hermes_env and hermes_env.exists() else {}
        if not api_key:
            api_key = (
                fallback_env.get("OPENROUTER_API_KEY")
                or fallback_env.get("OPENAI_API_KEY")
                or ""
            )

        # If Xanax is still on the default local Ollama-ish config, prefer Hermes' config.
        if (
            base_url.rstrip("/") == "http://localhost:11434"
            and hermes_config
            and hermes_config.exists()
        ):
            config_text = hermes_config.read_text(encoding="utf-8", errors="ignore")
            base_url = self._extract_yaml_value(config_text, "model", "base_url") or base_url
            model = self._extract_yaml_value(config_text, "model", "default") or model

        base_url = base_url.rstrip("/")
        return base_url, model, api_key

    @staticmethod
    def _extract_yaml_value(text: str, section: str, key: str) -> str | None:
        """
        Very small YAML reader for the Hermes config shape we care about.

        We avoid adding a new YAML dependency for a couple of values.
        """
        section_pattern = rf"^{re.escape(section)}:\s*$"
        lines = text.splitlines()
        in_section = False
        indent = None
        for line in lines:
            if not in_section:
                if re.match(section_pattern, line):
                    in_section = True
                continue

            if not line.strip():
                continue
            current_indent = len(line) - len(line.lstrip(" "))
            if indent is None:
                indent = current_indent
            if current_indent < indent:
                break

            match = re.match(rf"^\s*{re.escape(key)}:\s*(.+?)\s*$", line)
            if match:
                value = match.group(1).strip()
                if value.startswith(("'", '"')) and value.endswith(("'", '"')):
                    value = value[1:-1]
                return value
        return None

    @staticmethod
    def _build_headers(api_key: str) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def is_alive(self) -> bool:
        """Return True if the configured Hermes-backed chat endpoint is reachable."""
        if not self.base_url:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/models", headers=self._headers)
                return response.status_code == 200
        except Exception:
            return False

    async def ensure_gateway_running(self, startup_wait: float = 0.0) -> bool:
        """
        Kept for compatibility with older startup code.

        Xanax no longer owns a separate Hermes backend process.
        """
        return await self.is_alive()

    async def stop_gateway(self) -> None:
        """No-op for compatibility."""
        return

    async def create_session(self, title: str = "Xanax Chat") -> str:
        async with self._lock:
            session_id = str(uuid4())
            self._sessions[session_id] = ChatSession(session_id=session_id, title=title)
            return session_id

    async def list_sessions(self) -> list[dict]:
        async with self._lock:
            sessions = list(self._sessions.values())
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return [session.to_dict() for session in sessions]

    async def get_session(self, session_id: str) -> dict | None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            data = session.to_dict()
            data["messages"] = session.messages.copy()
            return data

    async def get_messages(self, session_id: str) -> list[dict]:
        async with self._lock:
            session = self._sessions.get(session_id)
            return session.messages.copy() if session else []

    async def delete_session(self, session_id: str) -> bool:
        async with self._lock:
            return self._sessions.pop(session_id, None) is not None

    async def _ensure_session(self, session_id: str, title: str = "Xanax Chat") -> ChatSession:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = ChatSession(session_id=session_id, title=title)
                self._sessions[session_id] = session
            return session

    def _session_payload(self, session: ChatSession, new_message: str) -> list[dict]:
        payload = [{"role": msg["role"], "content": msg["content"]} for msg in session.messages]
        payload.append({"role": "user", "content": new_message})
        return payload

    async def chat_stream(self, session_id: str, message: str) -> AsyncIterator[str]:
        """
        Stream a chat response from the configured Hermes-backed model.

        Xanax stores the conversation locally and sends the full history to the
        OpenAI-compatible endpoint.
        """
        session = await self._ensure_session(session_id)
        assistant_chunks: list[str] = []

        async with self._lock:
            session.messages.append({"role": "user", "content": message})
            session.updated_at = time.time()
            messages = [msg.copy() for msg in session.messages]

        payload = {"model": self.model, "messages": messages, "stream": True}

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = (
                                chunk.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if delta:
                                assistant_chunks.append(delta)
                                yield delta
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue

            async with self._lock:
                session.messages.append({"role": "assistant", "content": "".join(assistant_chunks)})
                session.updated_at = time.time()
        except httpx.HTTPStatusError as e:
            logger.error("Chat backend HTTP %s: %s", e.response.status_code, e)
            yield f"\n\n[Hermes error: HTTP {e.response.status_code}]"
        except Exception as e:
            logger.exception("Hermes chat_stream failed")
            yield f"\n\n[Xanax error: {e}]"

    async def stream_with_context(self, messages: list[dict]) -> AsyncIterator[str]:
        """
        Stream a response given a fully-assembled messages list.
        Bypasses the in-memory session store — callers own the history.
        """
        payload = {"model": self.model, "messages": messages, "stream": True}
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = (
                                chunk.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue
        except httpx.HTTPStatusError as e:
            yield f"\n\n[Hermes error: HTTP {e.response.status_code}]"
        except Exception as e:
            logger.exception("stream_with_context failed")
            yield f"\n\n[Xanax error: {e}]"

    async def complete_with_context(self, messages: list[dict]) -> str:
        """One-shot (non-streaming) completion with caller-supplied messages."""
        payload = {"model": self.model, "messages": messages, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
        except Exception:
            logger.exception("complete_with_context failed")
            return ""

    async def chat_once(self, session_id: str, message: str) -> str:
        chunks = []
        async for chunk in self.chat_stream(session_id, message):
            chunks.append(chunk)
        return "".join(chunks)


hermes = HermesBridge()
