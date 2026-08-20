"""Interactive web login sessions for subscription-backed CLI model entries.

Only the two fixed commands in this module can be launched. Client messages can
submit Claude's authorization code or cancel a session; they never influence a
command, argument, environment-variable name, or credential directory.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
from contextlib import suppress
from typing import Any

from api.agents.subprocess_util import _kill_process_tree, stream_proc
from core.cli_provider import (
    _CLAUDE_FALLBACK,
    _CODEX_FALLBACK,
    _resolve_bin,
    build_clean_env,
)
from core.provider_errors import safe_provider_error

logger = logging.getLogger("xanax.cli_login")

LOGIN_TTL_SECONDS = 15 * 60
START_TIMEOUT_SECONDS = 30.0
STATUS_TIMEOUT_SECONDS = 20.0
_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_URL_RE = re.compile(r"https://[^\s\x00-\x1f]+")


def parse_jsonrpc_line(line: str | bytes) -> dict[str, Any] | None:
    """Parse one app-server JSONL record, ignoring unrelated CLI output."""
    if isinstance(line, bytes):
        line = line.decode("utf-8", errors="replace")
    try:
        value = json.loads(line.strip())
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


class LoginSessionConflict(RuntimeError):
    pass


class LoginSessionError(RuntimeError):
    pass


class _InteractiveProcess:
    """Small async facade over Popen, with a PTY for Claude on POSIX."""

    def __init__(self, command: list[str], env: dict[str, str], *, use_pty: bool):
        self.command = command
        self.env = env
        self.use_pty = use_pty and os.name == "posix"
        self.proc: subprocess.Popen | None = None
        self._master_fd: int | None = None

    async def start(self) -> None:
        await asyncio.to_thread(self._start_blocking)

    def _start_blocking(self) -> None:
        options = {"start_new_session": True} if os.name == "posix" else {}
        if self.use_pty:
            master_fd, slave_fd = os.openpty()
            try:
                # Keep the long OAuth URL on one logical terminal line.
                import fcntl
                import struct
                import termios
                fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 4096, 0, 0))
                self.proc = subprocess.Popen(
                    self.command, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                    env=self.env, close_fds=True, **options,
                )
                self._master_fd = master_fd
            except Exception:
                os.close(master_fd)
                raise
            finally:
                os.close(slave_fd)
            return

        self.proc = subprocess.Popen(
            self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, env=self.env, **options,
        )

    async def read(self) -> bytes:
        return await asyncio.to_thread(self._read_blocking)

    def _read_blocking(self) -> bytes:
        try:
            if self._master_fd is not None:
                return os.read(self._master_fd, 4096)
            if self.proc and self.proc.stdout:
                return self.proc.stdout.readline()
        except OSError:
            return b""
        return b""

    async def write(self, data: bytes) -> None:
        await asyncio.to_thread(self._write_blocking, data)

    def _write_blocking(self, data: bytes) -> None:
        if self._master_fd is not None:
            os.write(self._master_fd, data)
            return
        if not self.proc or not self.proc.stdin:
            raise BrokenPipeError("CLI stdin is unavailable")
        self.proc.stdin.write(data)
        self.proc.stdin.flush()

    async def terminate(self) -> None:
        proc = self.proc
        if proc and proc.poll() is None:
            await asyncio.to_thread(_kill_process_tree, proc)
        if self._master_fd is not None:
            with suppress(OSError):
                os.close(self._master_fd)
            self._master_fd = None


class CliLoginSession:
    def __init__(self, entry: dict):
        self.entry = entry
        self.model_pool_id = int(entry["id"])
        self.events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.done = asyncio.Event()
        self._finished = False
        self._timeout_task: asyncio.Task | None = None

    async def start(self) -> dict[str, Any]:
        raise NotImplementedError

    def arm_timeout(self) -> None:
        self._timeout_task = asyncio.create_task(self._expire())

    async def _expire(self) -> None:
        await asyncio.sleep(LOGIN_TTL_SECONDS)
        if not self.done.is_set():
            await self.cancel(expired=True)

    async def next_event(self) -> dict[str, Any]:
        return await self.events.get()

    async def _finish(self, event: dict[str, Any]) -> None:
        if self._finished:
            return
        self._finished = True
        await self.events.put(event)
        self.done.set()

    async def submit_code(self, _code: str) -> None:
        raise LoginSessionError("This login flow does not accept a code")

    async def cancel(self, *, expired: bool = False) -> None:
        await self._finish({"type": "cancelled", "expired": expired})

    async def close(self) -> None:
        if self._timeout_task:
            self._timeout_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._timeout_task


class CodexLoginSession(CliLoginSession):
    def __init__(self, entry: dict):
        super().__init__(entry)
        config_dir = str(entry.get("cli_config_dir") or "").strip()
        env = build_clean_env({"CODEX_HOME": config_dir} if config_dir else None)
        self._process = _InteractiveProcess(
            [_resolve_bin("codex", _CODEX_FALLBACK), "app-server"], env, use_pty=False,
        )
        self._reader_task: asyncio.Task | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._next_id = 1
        self._login_id = ""

    async def start(self) -> dict[str, Any]:
        await self._process.start()
        self._reader_task = asyncio.create_task(self._read_messages())
        await self._request(
            "initialize",
            {"clientInfo": {"name": "xanax-hub", "title": "Xanax Hub", "version": "0.1.0"}},
        )
        await self._notify("initialized", {})
        result = await self._request("account/login/start", {"type": "chatgptDeviceCode"})
        if not isinstance(result, dict):
            raise LoginSessionError("Codex returned an invalid login response")
        self._login_id = str(result.get("loginId") or "")
        verification_url = str(result.get("verificationUrl") or "")
        user_code = str(result.get("userCode") or "")
        if not self._login_id or not verification_url or not user_code:
            raise LoginSessionError("Codex did not return a device code")
        return {
            "type": "started", "api_style": "codex_cli",
            "verificationUrl": verification_url, "userCode": user_code,
        }

    async def _request(self, method: str, params: dict) -> Any:
        request_id = self._next_id
        self._next_id += 1
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        await self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        try:
            response = await asyncio.wait_for(future, START_TIMEOUT_SECONDS)
        finally:
            self._pending.pop(request_id, None)
        if response.get("error"):
            raise LoginSessionError(safe_provider_error(response["error"], self.entry))
        return response.get("result")

    async def _notify(self, method: str, params: dict) -> None:
        await self._send({"jsonrpc": "2.0", "method": method, "params": params})

    async def _send(self, payload: dict) -> None:
        data = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        await self._process.write(data)

    async def _read_messages(self) -> None:
        buffer = ""
        try:
            while True:
                chunk = await self._process.read()
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    await self._handle_message(parse_jsonrpc_line(line))
            if buffer.strip():
                await self._handle_message(parse_jsonrpc_line(buffer))
            if not self.done.is_set():
                await self._finish({"type": "completed", "success": False, "error": "Codex login ended before completion"})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Codex login reader failed for model pool %s (%s)", self.model_pool_id, type(exc).__name__)
            await self._finish({"type": "error", "message": "Codex login channel failed"})

    async def _handle_message(self, message: dict[str, Any] | None) -> None:
        if not message:
            return
        request_id = message.get("id")
        if isinstance(request_id, int) and request_id in self._pending:
            future = self._pending[request_id]
            if not future.done():
                future.set_result(message)
            return
        if message.get("method") != "account/login/completed":
            return
        params = message.get("params") or {}
        if self._login_id and params.get("loginId") != self._login_id:
            return
        success = params.get("success") is True
        error = None if success else safe_provider_error(params.get("error"), self.entry)
        await self._finish({"type": "completed", "success": success, "error": error})

    async def cancel(self, *, expired: bool = False) -> None:
        if self.done.is_set():
            return
        if self._login_id:
            with suppress(Exception):
                request_id = self._next_id
                self._next_id += 1
                await self._send({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "account/login/cancel",
                    "params": {"loginId": self._login_id},
                })
        await super().cancel(expired=expired)
        await self._process.terminate()

    async def close(self) -> None:
        await super().close()
        await self._process.terminate()
        if self._reader_task:
            self._reader_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._reader_task


class ClaudeLoginSession(CliLoginSession):
    def __init__(self, entry: dict):
        super().__init__(entry)
        config_dir = str(entry.get("cli_config_dir") or "").strip()
        env = build_clean_env({"CLAUDE_CONFIG_DIR": config_dir} if config_dir else None)
        self._process = _InteractiveProcess(
            [_resolve_bin("claude", _CLAUDE_FALLBACK), "auth", "login", "--claudeai"],
            env, use_pty=True,
        )
        self._reader_task: asyncio.Task | None = None
        self._url_future: asyncio.Future | None = None
        self._needs_code_sent = False

    async def start(self) -> dict[str, Any]:
        await self._process.start()
        self._url_future = asyncio.get_running_loop().create_future()
        self._reader_task = asyncio.create_task(self._read_output())
        auth_url = await asyncio.wait_for(self._url_future, START_TIMEOUT_SECONDS)
        return {"type": "started", "api_style": "claude_cli", "authUrl": auth_url}

    async def _read_output(self) -> None:
        visible = ""
        try:
            while True:
                chunk = await self._process.read()
                if not chunk:
                    break
                visible = (visible + _ANSI_RE.sub("", chunk.decode("utf-8", errors="replace")))[-32768:]
                if self._url_future and not self._url_future.done():
                    match = _URL_RE.search(visible)
                    if match:
                        self._url_future.set_result(match.group(0).rstrip("'\"),.;"))
                if not self._needs_code_sent and "Paste code here if prompted >" in visible:
                    self._needs_code_sent = True
                    await self.events.put({"type": "needs_code"})

            if self._url_future and not self._url_future.done():
                self._url_future.set_exception(
                    LoginSessionError("Claude did not return an authentication URL")
                )
            if not self.done.is_set():
                status = await read_cli_auth_status(self.entry)
                success = status.get("logged_in") is True
                await self._finish({
                    "type": "completed", "success": success,
                    "error": None if success else status.get("error") or "Claude login was not confirmed",
                })
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Claude login reader failed for model pool %s (%s)", self.model_pool_id, type(exc).__name__)
            await self._finish({"type": "error", "message": "Claude login channel failed"})

    async def submit_code(self, code: str) -> None:
        if self.done.is_set():
            return
        normalized = code.strip()
        if not normalized or len(normalized) > 8192 or "\n" in normalized or "\r" in normalized:
            raise LoginSessionError("Invalid authorization code")
        await self._process.write((normalized + "\n").encode("utf-8"))

    async def cancel(self, *, expired: bool = False) -> None:
        if self.done.is_set():
            return
        await super().cancel(expired=expired)
        await self._process.terminate()

    async def close(self) -> None:
        await super().close()
        await self._process.terminate()
        if self._reader_task:
            self._reader_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._reader_task


class CliLoginManager:
    """Own active sessions and enforce one login per model-pool entry."""

    def __init__(self):
        self._sessions: dict[int, CliLoginSession] = {}
        self._lock = asyncio.Lock()

    def _make_session(self, entry: dict) -> CliLoginSession:
        if entry.get("api_style") == "codex_cli":
            return CodexLoginSession(entry)
        if entry.get("api_style") == "claude_cli":
            return ClaudeLoginSession(entry)
        raise LoginSessionError("This model does not use a supported CLI login")

    async def start(self, entry: dict) -> tuple[CliLoginSession, dict[str, Any]]:
        model_pool_id = int(entry["id"])
        async with self._lock:
            current = self._sessions.get(model_pool_id)
            if current and not current.done.is_set():
                raise LoginSessionConflict("A login session is already active for this model")
            session = self._make_session(entry)
            self._sessions[model_pool_id] = session
        try:
            started = await session.start()
            session.arm_timeout()
            asyncio.create_task(self._remove_when_done(model_pool_id, session))
            return session, started
        except Exception:
            await self.release(model_pool_id, session, cancel=False)
            raise

    async def _remove_when_done(self, model_pool_id: int, session: CliLoginSession) -> None:
        await session.done.wait()
        async with self._lock:
            if self._sessions.get(model_pool_id) is session:
                self._sessions.pop(model_pool_id, None)

    async def release(self, model_pool_id: int, session: CliLoginSession, *, cancel: bool = True) -> None:
        async with self._lock:
            if self._sessions.get(model_pool_id) is session:
                self._sessions.pop(model_pool_id, None)
        if cancel and not session.done.is_set():
            await session.cancel()
        await session.close()

    async def close_all(self) -> None:
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        await asyncio.gather(*(session.cancel() for session in sessions), return_exceptions=True)
        await asyncio.gather(*(session.close() for session in sessions), return_exceptions=True)


async def _codex_auth_status(entry: dict) -> dict[str, Any]:
    config_dir = str(entry.get("cli_config_dir") or "").strip()
    env = build_clean_env({"CODEX_HOME": config_dir} if config_dir else None)
    process = _InteractiveProcess(
        [_resolve_bin("codex", _CODEX_FALLBACK), "app-server"], env, use_pty=False,
    )
    next_id = 1

    async def request(method: str, params: dict) -> dict:
        nonlocal next_id
        request_id = next_id
        next_id += 1
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        await process.write((json.dumps(payload, separators=(",", ":")) + "\n").encode())
        while True:
            raw = await process.read()
            if not raw:
                raise LoginSessionError("Codex app-server exited while checking authentication")
            for line in raw.decode("utf-8", errors="replace").splitlines():
                message = parse_jsonrpc_line(line)
                if message and message.get("id") == request_id:
                    return message

    await process.start()
    try:
        initialized = await asyncio.wait_for(request(
            "initialize",
            {"clientInfo": {"name": "xanax-hub", "title": "Xanax Hub", "version": "0.1.0"}},
        ), STATUS_TIMEOUT_SECONDS)
        if initialized.get("error"):
            raise LoginSessionError("Codex app-server initialization failed")
        await process.write(b'{"jsonrpc":"2.0","method":"initialized","params":{}}\n')
        response = await asyncio.wait_for(request("getAuthStatus", {}), STATUS_TIMEOUT_SECONDS)
        if response.get("error"):
            response = await asyncio.wait_for(request("account/read", {}), STATUS_TIMEOUT_SECONDS)
        if response.get("error"):
            raise LoginSessionError("Codex app-server could not read authentication status")
        result = response.get("result") or {}
        auth_status = result.get("authStatus")
        account = result.get("account")
        logged_in = bool(account) or auth_status not in (None, "notLoggedIn", "loggedOut", "none")
        return {"api_style": "codex_cli", "logged_in": logged_in, "status": "logged_in" if logged_in else "logged_out"}
    finally:
        await process.terminate()


async def _claude_auth_status(entry: dict) -> dict[str, Any]:
    config_dir = str(entry.get("cli_config_dir") or "").strip()
    env = build_clean_env({"CLAUDE_CONFIG_DIR": config_dir} if config_dir else None)
    command = [_resolve_bin("claude", _CLAUDE_FALLBACK), "auth", "status"]
    parsed: dict[str, Any] | None = None
    async for tag, data in stream_proc(command, env=env, timeout=STATUS_TIMEOUT_SECONDS):
        if tag == "stdout":
            try:
                candidate = json.loads(data)
                if isinstance(candidate, dict):
                    parsed = candidate
            except json.JSONDecodeError:
                continue
    if parsed is None:
        raise LoginSessionError("Claude CLI did not return authentication status")
    logged_in = parsed.get("loggedIn") is True
    result: dict[str, Any] = {
        "api_style": "claude_cli", "logged_in": logged_in,
        "status": "logged_in" if logged_in else "logged_out",
    }
    if logged_in:
        result["auth_method"] = str(parsed.get("authMethod") or "")
        result["subscription_type"] = str(parsed.get("subscriptionType") or "")
    return result


async def read_cli_auth_status(entry: dict) -> dict[str, Any]:
    if entry.get("api_style") == "codex_cli":
        return await _codex_auth_status(entry)
    if entry.get("api_style") == "claude_cli":
        return await _claude_auth_status(entry)
    raise LoginSessionError("This model does not use CLI authentication")


cli_login_manager = CliLoginManager()
