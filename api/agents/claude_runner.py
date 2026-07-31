"""
Subprocess wrapper for Claude CLI (-p non-interactive mode).

Uses thread-based subprocess streaming to avoid ProactorEventLoop requirement
on Windows (asyncio.create_subprocess_exec raises NotImplementedError with
SelectorEventLoop used by uvicorn).

Yields dicts:
  {"type": "text",  "content": "..."}             — assistant text
  {"type": "tool",  "content": "..."}             — tool call summary
  {"type": "error", "content": "..."}             — stderr / error result
  {"type": "done",  "content": "", "ok": bool}    — finished
"""
from __future__ import annotations

import json
import logging
import shutil
from typing import AsyncIterator

from api.agents.subprocess_util import stream_proc

logger = logging.getLogger("xanax.agents.claude")

_FALLBACK = r"C:\Users\Quang\.local\bin\claude.EXE"


def _build_cmd(prompt: str) -> list[str]:
    bin_ = shutil.which("claude") or _FALLBACK
    return [
        bin_, "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--permission-mode", "auto",
    ]


async def run(prompt: str, cwd: str | None = None) -> AsyncIterator[dict]:
    cmd = _build_cmd(prompt)
    logger.debug("claude: %s (cwd=%s)", cmd[0], cwd)

    had_error = False

    try:
        async for tag, data in stream_proc(cmd, cwd=cwd):
            if tag == "stdout":
                try:
                    obj = json.loads(data)
                    t = obj.get("type", "")

                    if t == "assistant":
                        for block in obj.get("message", {}).get("content", []):
                            bt = block.get("type", "")
                            if bt == "text":
                                yield {"type": "text", "content": block["text"]}
                            elif bt == "tool_use":
                                name = block.get("name", "tool")
                                inp  = json.dumps(block.get("input", {}), ensure_ascii=False)
                                yield {"type": "tool", "content": f"⚙ {name}: {inp[:300]}"}

                    elif t == "result":
                        if obj.get("is_error") or obj.get("subtype", "") != "success":
                            had_error = True
                            msg = obj.get("result") or obj.get("error") or json.dumps(obj)
                            yield {"type": "error", "content": str(msg)}

                    # system, user, rate_limit_event → skip

                except json.JSONDecodeError:
                    yield {"type": "text", "content": data}

            elif tag == "stderr":
                # Claude CLI with --verbose writes progress/debug lines to stderr.
                # Only treat as error if the line looks like an actual error.
                low = data.lower()
                is_real_error = (
                    "error" in low
                    or "fatal" in low
                    or "traceback" in low
                    or "exception" in low
                )
                if is_real_error:
                    had_error = True
                    yield {"type": "error", "content": data}
                else:
                    logger.debug("claude stderr: %s", data)

            elif tag == "error":
                had_error = True
                yield {"type": "error", "content": data}

            elif tag == "exit":
                rc = int(data)
                if rc not in (0,):
                    had_error = True

    except Exception as exc:
        logger.exception("claude runner error")
        had_error = True
        yield {"type": "error", "content": str(exc)}

    yield {"type": "done", "content": "", "ok": not had_error}
