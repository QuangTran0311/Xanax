"""
Subprocess wrapper for Codex CLI (codex exec --json).

Key fixes vs naive approach:
- Prompt is passed via STDIN (using `-` sentinel), not as a CLI arg.
  Multi-line prompts with markdown/special chars break cmd.exe escaping.
- On Windows, npm .CMD wrappers are invoked via `cmd /c`.
- Codex's actual JSONL event schema is handled (item.completed, etc.)
- The "Reading additional input from stdin" stderr warning is suppressed.

Yields dicts:
  {"type": "text",    "content": "..."}
  {"type": "shell",   "content": "..."}
  {"type": "output",  "content": "..."}
  {"type": "file",    "content": "..."}
  {"type": "error",   "content": "..."}
  {"type": "done",    "content": "", "ok": bool}
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
from typing import AsyncIterator

from api.agents.subprocess_util import stream_proc
from core.cli_provider import build_clean_env

logger = logging.getLogger("xanax.agents.codex")

_FALLBACK = r"C:\Users\Quang\AppData\Roaming\npm\codex.CMD"

# Codex stderr lines that are informational noise, not real errors
_STDERR_IGNORE = {
    "reading additional input from stdin",
}


def _build_cmd(cwd: str | None) -> list[str]:
    bin_ = shutil.which("codex") or _FALLBACK

    # `-` tells Codex to read the prompt from stdin
    args = ["exec", "--json", "-s", "workspace-write", "-"]
    if cwd:
        args = ["exec", "--json", "-s", "workspace-write", "-C", cwd, "-"]

    if sys.platform == "win32" and bin_.upper().endswith(".CMD"):
        return ["cmd", "/c", bin_] + args

    return [bin_] + args


async def run(prompt: str, cwd: str | None = None) -> AsyncIterator[dict]:
    cmd = _build_cmd(cwd)
    stdin_bytes = prompt.encode("utf-8")
    logger.debug("codex: %s (cwd=%s, prompt_len=%d)", cmd[:4], cwd, len(prompt))

    had_error = False

    try:
        # env đã xoá OPENAI_*/ANTHROPIC_* để CLI dùng đăng nhập gói, không bị
        # một biến sót lại trong môi trường server đẩy sang endpoint bên thứ 3.
        async for tag, data in stream_proc(
            cmd, stdin_data=stdin_bytes, env=build_clean_env()
        ):
            if tag == "stdout":
                try:
                    obj = json.loads(data)
                    ev = _map_event(obj)
                    if ev is None:
                        continue          # skip known noise events
                    if ev["type"] == "error":
                        had_error = True
                    yield ev
                except json.JSONDecodeError:
                    # plain text line — show as-is
                    yield {"type": "text", "content": data}

            elif tag == "stderr":
                # Suppress known informational warnings from Codex
                if data.lower().strip().lstrip("⚠ ") in _STDERR_IGNORE:
                    continue
                if any(ig in data.lower() for ig in _STDERR_IGNORE):
                    continue
                had_error = True
                yield {"type": "error", "content": data}

            elif tag == "error":
                had_error = True
                yield {"type": "error", "content": data}

            elif tag == "exit":
                if int(data) not in (0,):
                    had_error = True

    except Exception as exc:
        logger.exception("codex runner error")
        had_error = True
        yield {"type": "error", "content": str(exc)}

    yield {"type": "done", "content": "", "ok": not had_error}


def _map_event(obj: dict) -> dict | None:
    """
    Map a Codex JSONL event to our internal event dict.
    Returns None for events that should be silently skipped.

    Codex --json format (observed):
      {"type": "thread.started", "thread_id": "..."}
      {"type": "turn.started"}
      {"type": "item.created",   "item": {...}}
      {"type": "item.output_text.delta", "item_id": "...", "delta": "..."}
      {"type": "item.completed", "item": {"type": "agent_message", "text": "..."}}
      {"type": "item.completed", "item": {"type": "function_call", ...}}
      {"type": "item.completed", "item": {"type": "function_call_output", "output": "..."}}
      {"type": "turn.completed", "usage": {...}}
      {"type": "thread.completed"}
    """
    t = obj.get("type", "")

    # ── Skip / noise ─────────────────────────────────────────────────────────
    if t in ("thread.started", "thread.completed", "turn.started",
             "turn.completed", "item.created", "item.started", "item.updated",
             "response.created", "response.in_progress", "response.completed",
             "rate_limit_updated", "session.created"):
        return None

    # ── Streaming text delta ──────────────────────────────────────────────────
    if t == "item.output_text.delta":
        delta = obj.get("delta", "")
        return {"type": "text", "content": delta} if delta else None

    # ── Completed items ───────────────────────────────────────────────────────
    if t == "item.completed":
        item = obj.get("item", {})
        item_type = item.get("type", "")

        if item_type == "agent_message":
            text = item.get("text", "") or item.get("content", "")
            if isinstance(text, list):
                text = "".join(b.get("text", "") for b in text if b.get("type") == "text")
            return {"type": "text", "content": str(text)} if text else None

        if item_type == "function_call":
            name = item.get("name", "shell")
            args = item.get("arguments", "")
            if isinstance(args, str):
                try:
                    args_obj = json.loads(args)
                    cmd = args_obj.get("command", args_obj.get("cmd", args))
                except json.JSONDecodeError:
                    cmd = args
            elif isinstance(args, dict):
                cmd = args.get("command", args.get("cmd", json.dumps(args)))
            else:
                cmd = str(args)
            return {"type": "shell", "content": f"$ [{name}] {cmd}"}

        if item_type == "function_call_output":
            out = item.get("output", "")
            return {"type": "output", "content": str(out)} if out else None

        if item_type in ("file_write", "patch"):
            path = item.get("path", item.get("file", ""))
            return {"type": "file", "content": f"📝 {path}"}

        if item_type == "command_execution":
            cmd = item.get("command", "")
            out = item.get("aggregated_output", "")
            status = item.get("status", "")
            if status == "completed" and cmd:
                return {"type": "shell", "content": cmd}
            if out and out.strip():
                return {"type": "output", "content": out.strip()}
            return None

        if item_type == "error":
            return {"type": "error", "content": item.get("message", str(item))}

        # Unknown item type — skip silently
        return None

    # ── Legacy / fallback event shapes ───────────────────────────────────────
    if t in ("message", "agent_message"):
        role    = obj.get("role", "")
        content = obj.get("content", "")
        if isinstance(content, list):
            content = "".join(b.get("text", "") for b in content if b.get("type") == "text")
        prefix = "🤖 " if role == "assistant" else ""
        return {"type": "text", "content": prefix + str(content)} if content else None

    if t in ("function_call", "shell_call", "tool_call"):
        name = obj.get("name", "shell")
        args = obj.get("arguments", obj.get("input", {}))
        cmd  = args.get("command", json.dumps(args)) if isinstance(args, dict) else str(args)
        return {"type": "shell", "content": f"$ [{name}] {cmd}"}

    if t in ("function_call_output", "shell_output", "tool_output"):
        out = obj.get("output", obj.get("content", ""))
        return {"type": "output", "content": str(out)} if out else None

    if t == "error":
        return {"type": "error", "content": obj.get("message", str(obj))}

    # Unknown event type — skip silently
    return None
