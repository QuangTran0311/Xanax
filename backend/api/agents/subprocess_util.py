"""
Thread-based async subprocess streaming for Windows compatibility.

`asyncio.create_subprocess_exec` requires ProactorEventLoop on Windows,
but uvicorn runs with SelectorEventLoop — so we use subprocess.Popen
in a background thread and push lines to an asyncio.Queue instead.
"""
from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import threading
import time
from typing import AsyncIterator


_KILL_GRACE_SECONDS = 5.0


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """Dừng CLI và các tiến trình con của nó, rồi cưỡng chế nếu cần.

    Trên POSIX, mỗi CLI được đặt vào một session riêng nên PID của tiến trình
    cũng là process-group ID. Trên Windows không có ``killpg`` tương đương;
    giữ đường ``terminate``/``kill`` để tương thích với SelectorEventLoop.
    """
    if os.name == "posix":
        try:
            group_id = os.getpgid(proc.pid)
        except ProcessLookupError:
            # Tiến trình cha có thể vừa thoát nhưng tiến trình con trong group
            # vẫn còn giữ pipe; group ID vẫn chính là PID lúc tạo session.
            group_id = proc.pid

        try:
            os.killpg(group_id, signal.SIGTERM)
        except ProcessLookupError:
            return

        deadline = time.monotonic() + _KILL_GRACE_SECONDS
        while time.monotonic() < deadline:
            try:
                os.killpg(group_id, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            try:
                os.killpg(group_id, signal.SIGKILL)
            except ProcessLookupError:
                pass

        try:
            proc.wait(timeout=_KILL_GRACE_SECONDS)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            pass
        return

    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=_KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=_KILL_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            pass
    except ProcessLookupError:
        pass


async def stream_proc(
    cmd: list[str],
    cwd: str | None = None,
    stdin_data: bytes | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
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
    timeout:    giới hạn tổng thời gian chạy, tính từ lúc tạo tiến trình.
                None giữ hành vi không giới hạn cũ.
    """
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
    proc: subprocess.Popen | None = None
    proc_lock = threading.Lock()
    kill_lock = threading.Lock()
    queue_lock = threading.Lock()
    stop_requested = threading.Event()
    worker_done = threading.Event()
    timed_out = threading.Event()
    terminal_sent = False

    def _put(t: str, d: str) -> None:
        nonlocal terminal_sent
        with queue_lock:
            if terminal_sent:
                return
            try:
                loop.call_soon_threadsafe(queue.put_nowait, (t, d))
            except RuntimeError:
                # Event loop đã đóng (thường do WebSocket/client biến mất).
                # Thread nền không được phun traceback vào journald.
                pass

    def _finish(error: str | None, exit_code: str) -> None:
        """Đẩy bộ tag kết thúc nguyên khối để ``exit`` luôn là tag cuối."""
        nonlocal terminal_sent
        with queue_lock:
            if terminal_sent:
                return
            try:
                if error is not None:
                    loop.call_soon_threadsafe(queue.put_nowait, ("error", error))
                loop.call_soon_threadsafe(queue.put_nowait, ("exit", exit_code))
            except RuntimeError:
                pass
            terminal_sent = True

    def _stop_process(current: subprocess.Popen) -> None:
        # Timeout và GeneratorExit có thể đến sát nhau; chỉ một thread thực hiện
        # chuỗi TERM -> chờ -> KILL tại một thời điểm.
        with kill_lock:
            _kill_process_tree(current)

    def _read_pipe(pipe, tag: str) -> None:
        try:
            for raw in pipe:
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line:
                    _put(tag, line)
        except Exception as exc:
            _put("error", f"pipe read error ({tag}): {exc}")

    def _run() -> None:
        nonlocal proc
        timer: threading.Timer | None = None
        try:
            popen_options = {"start_new_session": True} if os.name == "posix" else {}
            current = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
                cwd=cwd,
                env=env,
                **popen_options,
            )
            with proc_lock:
                proc = current

            def _on_timeout() -> None:
                if worker_done.is_set():
                    return
                timed_out.set()
                _stop_process(current)

            # Timer độc lập tính tổng thời gian chạy, không phụ thuộc CLI có liên
            # tục xuất dữ liệu hay đang kẹt lúc ghi stdin/đọc pipe.
            if timeout is not None:
                timer = threading.Timer(timeout, _on_timeout)
                timer.daemon = True
                timer.start()

            if stop_requested.is_set():
                _stop_process(current)

            if stdin_data is not None:
                try:
                    current.stdin.write(stdin_data)
                    current.stdin.close()
                except Exception:
                    pass

            t_out = threading.Thread(target=_read_pipe, args=(current.stdout, "stdout"), daemon=True)
            t_err = threading.Thread(target=_read_pipe, args=(current.stderr, "stderr"), daemon=True)
            t_out.start()
            t_err.start()
            current.wait()

            if timed_out.is_set() or stop_requested.is_set():
                # Sau khi kill, pipe thường đóng ngay. Vẫn giới hạn tổng thời
                # gian join để một pipe bất thường không giữ thread này mãi.
                join_deadline = time.monotonic() + _KILL_GRACE_SECONDS
                for reader in (t_out, t_err):
                    reader.join(max(0.0, join_deadline - time.monotonic()))
                # join(timeout=...) luôn trả None; phải hỏi is_alive() mới biết
                # reader còn kẹt hay không. Đóng đầu đọc là hàng rào cuối cùng
                # nếu một tiến trình con bất thường vẫn giữ descriptor của pipe.
                for reader in (t_out, t_err):
                    if reader.is_alive():
                        # Không đóng BufferedReader từ thread khác: close() có
                        # thể chờ chính lock của read đang bị kẹt. Một lần join
                        # ngắn cuối vẫn giữ đường hủy hoàn toàn hữu hạn.
                        reader.join(0.05)
            else:
                # timeout=None cố ý giữ nguyên hành vi chờ không giới hạn cũ.
                t_out.join()
                t_err.join()

            worker_done.set()
            if timed_out.is_set():
                _finish(
                    f"CLI vượt quá {timeout:g}s, đã hủy tiến trình",
                    "124",
                )
            else:
                _finish(None, str(current.returncode))

        except FileNotFoundError:
            _finish(f"binary not found: {cmd[0]!r}", "1")
        except Exception as exc:
            with proc_lock:
                current = proc
            if current is not None and not worker_done.is_set():
                _stop_process(current)
            _finish(str(exc), "1")
        finally:
            worker_done.set()
            if timer is not None:
                timer.cancel()

    threading.Thread(target=_run, daemon=True).start()

    try:
        while True:
            tag, data = await queue.get()
            yield tag, data
            if tag == "exit":
                break
    finally:
        stop_requested.set()
        with proc_lock:
            current = proc
        if current is not None and not worker_done.is_set():
            # Chạy đoạn chờ TERM/KILL ngoài event loop để việc đóng WebSocket
            # không làm đứng các request khác.
            await asyncio.to_thread(_stop_process, current)
