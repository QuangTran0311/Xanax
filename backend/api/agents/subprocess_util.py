"""
Thread-based async subprocess streaming for Windows compatibility.

`asyncio.create_subprocess_exec` requires ProactorEventLoop on Windows,
but uvicorn runs with SelectorEventLoop — so we use subprocess.Popen
in a background thread and push lines to an asyncio.Queue instead.
"""
from __future__ import annotations

import asyncio
import subprocess
import threading
from typing import AsyncIterator


async def stream_proc(
    cmd: list[str],
    cwd: str | None = None,
    stdin_data: bytes | None = None,
    env: dict[str, str] | None = None,
) -> AsyncIterator[tuple[str, str]]:
    """
    Run *cmd* in a thread and yield (tag, line) pairs:
      ('stdout', line)   — each stdout line
      ('stderr', line)   — each stderr line
      ('exit',   rc_str) — process exit code as string (always last)
      ('error',  msg)    — exception before/during process

    stdin_data: if provided, written to process stdin then stdin is closed.
                If None, stdin is DEVNULL.
    env:        full environment for the child. If None, the child inherits
                ours — which lets a stray ANTHROPIC_BASE_URL/OPENAI_BASE_URL in
                the server's environment silently route the CLI through a
                gateway. Callers that care pass a scrubbed env (see
                core.cli_provider.build_clean_env).
    """
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

    def _put(t: str, d: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, (t, d))

    def _read_pipe(pipe, tag: str) -> None:
        try:
            for raw in pipe:
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line:
                    _put(tag, line)
        except Exception as exc:
            _put("error", f"pipe read error ({tag}): {exc}")

    def _run() -> None:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
                cwd=cwd,
                env=env,
            )

            if stdin_data is not None:
                try:
                    proc.stdin.write(stdin_data)
                    proc.stdin.close()
                except Exception:
                    pass

            t_out = threading.Thread(target=_read_pipe, args=(proc.stdout, "stdout"), daemon=True)
            t_err = threading.Thread(target=_read_pipe, args=(proc.stderr, "stderr"), daemon=True)
            t_out.start()
            t_err.start()
            t_out.join()
            t_err.join()
            proc.wait()
            _put("exit", str(proc.returncode))

        except FileNotFoundError:
            _put("error", f"binary not found: {cmd[0]!r}")
            _put("exit", "1")
        except Exception as exc:
            _put("error", str(exc))
            _put("exit", "1")

    threading.Thread(target=_run, daemon=True).start()

    while True:
        tag, data = await queue.get()
        yield tag, data
        if tag == "exit":
            break
