"""Kiểm tra timeout và thu hoạch tiến trình CLI trên cả Windows lẫn POSIX."""
from __future__ import annotations

import sys
import time

import pytest

from api.agents import subprocess_util


_SLEEP_CMD = [sys.executable, "-c", "import time; time.sleep(30)"]


@pytest.mark.asyncio
async def test_stream_proc_timeout_tra_exit_124_trong_vai_giay():
    started = time.monotonic()
    events = [event async for event in subprocess_util.stream_proc(_SLEEP_CMD, timeout=0.1)]
    elapsed = time.monotonic() - started

    assert events == [
        ("error", "CLI vượt quá 0.1s, đã hủy tiến trình"),
        ("exit", "124"),
    ]
    assert elapsed < 5


@pytest.mark.asyncio
async def test_stream_proc_timeout_da_thu_hoach_tien_trinh(monkeypatch):
    real_popen = subprocess_util.subprocess.Popen
    spawned = []

    def tracking_popen(*args, **kwargs):
        proc = real_popen(*args, **kwargs)
        spawned.append(proc)
        return proc

    monkeypatch.setattr(subprocess_util.subprocess, "Popen", tracking_popen)

    events = [event async for event in subprocess_util.stream_proc(_SLEEP_CMD, timeout=0.1)]

    assert events[-1] == ("exit", "124")
    assert len(spawned) == 1
    assert spawned[0].poll() is not None


@pytest.mark.asyncio
async def test_dong_generator_thu_hoach_tien_trinh(monkeypatch):
    real_popen = subprocess_util.subprocess.Popen
    spawned = []

    def tracking_popen(*args, **kwargs):
        proc = real_popen(*args, **kwargs)
        spawned.append(proc)
        return proc

    monkeypatch.setattr(subprocess_util.subprocess, "Popen", tracking_popen)
    cmd = [
        sys.executable,
        "-u",
        "-c",
        "import time; print('ready', flush=True); time.sleep(30)",
    ]

    events = subprocess_util.stream_proc(cmd)
    assert await events.__anext__() == ("stdout", "ready")
    await events.aclose()

    assert len(spawned) == 1
    assert spawned[0].poll() is not None
