"""
Task-runner WebSocket — Xanax coordinates Claude CLI + Codex CLI.

Architecture:
  - Pipeline runs as asyncio.create_task() so the WS loop keeps receiving messages.
  - Human-in-the-loop: after each step, if review_mode=True, pipeline pauses and
    sends plan_ready / todos_ready events. User sends approve_plan / approve_todos.
  - Agent selection: client sends agents=["xanax","claude","codex"]; skipped agents
    are bypassed with sensible fallbacks.
  - Auto-retry: each step retries once on failure.
  - Rerun: rerun_from_claude / rerun_from_codex restart the pipeline from a step
    using saved outputs from the DB.

Client → Server:
  { "task": "...", "workdir": "...", "agents": [...], "review_mode": bool }
  { "action": "approve_plan",    "session_id": N, "plan": {...} }   -- or abort:true
  { "action": "approve_todos",   "session_id": N }                  -- or abort:true
  { "action": "rerun_from_claude", "session_id": N }
  { "action": "rerun_from_codex",  "session_id": N }
  { "action": "pass"|"fail"|"summarise"|"confirm_notes", "session_id": N, ... }

Server → Client:
  { "agent": "pipeline", "type": "session_created", "session_id": N }
  { "agent": "pipeline", "type": "step",            "step": 1|2|3, "content": "..." }
  { "agent": "pipeline", "type": "plan_ready",      "content": "<json>", "session_id": N }
  { "agent": "pipeline", "type": "todos_ready",     "content": "<text>", "session_id": N }
  { "agent": "pipeline", "type": "retrying",        "content": "..." }
  { "agent": "pipeline", "type": "done",            "session_id": N }
  { "agent": "pipeline", "type": "error",           "content": "...", "session_id": N }
  { "agent": "xanax"|"claude"|"codex", "type": "status"|"text"|...|"done"|"error" }
  { "agent": "pipeline", "type": "verdict_set",     "content": "pass"|"fail" }
  { "agent": "pipeline", "type": "notes_preview",   "content": "..." }
  { "agent": "pipeline", "type": "notes_saved" }
  { "agent": "pipeline", "type": "failure_analysed","content": "..." }
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from api.agents import claude_runner, codex_runner
from core.hermes_bridge import hermes
from hub.database import (
    add_pipeline_log,
    create_task_session,
    delete_agent_pipeline_logs,
    get_task_session,
    update_task_session,
)

logger = logging.getLogger("xanax.ws.task")
router = APIRouter()

_DEFAULT_WORKDIR = str(Path(__file__).parent.parent)

# ── Human-in-the-loop approval gates ─────────────────────────────────────────
# Keyed by session_id. Pipeline tasks wait on these events.
_approval_gates: dict[int, asyncio.Event] = {}
_approval_data:  dict[int, dict]           = {}


async def _wait_approval(session_id: int, timeout: float = 300.0) -> dict:
    """
    Pause the pipeline until user approves or timeout (5 min).
    Returns the data dict sent with the approval.
    On timeout, returns {} (auto-proceed).
    """
    event = asyncio.Event()
    _approval_gates[session_id] = event
    _approval_data.pop(session_id, None)
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
        return _approval_data.pop(session_id, {})
    except asyncio.TimeoutError:
        logger.warning("Approval timeout for session %s — auto-proceeding", session_id)
        return {}
    finally:
        _approval_gates.pop(session_id, None)


def _signal_approval(session_id: int, data: dict) -> None:
    _approval_data[session_id] = data
    if session_id in _approval_gates:
        _approval_gates[session_id].set()


# ── SOUL.md helpers ───────────────────────────────────────────────────────────

def _soul_path() -> Path:
    local = (
        os.environ.get("LOCALAPPDATA")
        or os.path.expandvars("%LOCALAPPDATA%")
        or str(Path.home() / "AppData" / "Local")
    )
    return Path(local) / "hermes" / "SOUL.md"


def _read_soul() -> str:
    p = _soul_path()
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _upsert_soul_task(session_id: int, title: str, content: str) -> None:
    p = _soul_path()
    if not p.exists():
        logger.warning("SOUL.md not found at %s — skipping upsert", p)
        return

    start_tag = f"<!-- TASK:{session_id} -->"
    end_tag   = f"<!-- /TASK:{session_id} -->"
    block     = f"{start_tag}\n**[Task] {title}**\n{content.strip()}\n{end_tag}"

    current = p.read_text(encoding="utf-8")
    if start_tag in current:
        pattern = re.escape(start_tag) + r".*?" + re.escape(end_tag)
        updated = re.sub(pattern, block, current, flags=re.DOTALL)
    else:
        marker = "## Ghi chú từ các session training"
        if marker in current:
            idx     = current.index(marker) + len(marker)
            updated = current[:idx] + "\n" + block + "\n" + current[idx:]
        else:
            updated = current.rstrip() + f"\n\n## Ghi chú từ các task runner\n{block}\n"

    p.write_text(updated, encoding="utf-8")
    logger.info("SOUL.md upserted for task session %s", session_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _emit(ws: WebSocket, agent: str, type_: str, content: str = "", **extra) -> None:
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_text(
                json.dumps({"agent": agent, "type": type_, "content": content, **extra},
                           ensure_ascii=False)
            )
    except Exception:
        pass


def _extract_json(text: str) -> dict | None:
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _make_title(task: str) -> str:
    task = task.strip().replace("\n", " ")
    return task[:60] + ("..." if len(task) > 60 else "")


# ── Pipeline steps ────────────────────────────────────────────────────────────

async def _step_xanax(
    ws: WebSocket, task: str, workdir: str, session_id: int
) -> tuple[dict | None, str]:
    await _emit(ws, "pipeline", "step", step=1, content="Xanax đang phân tích nhiệm vụ...")
    await _emit(ws, "xanax", "status", content="thinking")

    soul = _read_soul()
    messages: list[dict] = []
    if soul:
        messages.append({"role": "system", "content": soul})

    messages.append({"role": "user", "content": f"""Papa giao cho con nhiệm vụ sau:

---
{task}
---

Thư mục làm việc: {workdir}

Con hãy phân tích kỹ và tạo:
1. **plan_for_claude**: Kế hoạch tổng thể, ngữ cảnh kỹ thuật, những điều Claude cần biết để lên chi tiết.
2. **todos_for_codex**: Danh sách các bước thực thi code cụ thể cho Codex (mỗi bước là một hành động rõ ràng).

Trả lời ĐÚNG FORMAT JSON sau (không thêm text ngoài JSON):
{{
  "plan_for_claude": "mô tả kế hoạch...",
  "todos_for_codex": [
    "Bước 1: ...",
    "Bước 2: ...",
    "Bước 3: ..."
  ]
}}"""})

    response = await hermes.complete_with_context(messages)
    if not response:
        await _emit(ws, "xanax", "error", content="Xanax không phản hồi được")
        await add_pipeline_log(session_id, "xanax", "error", "Xanax không phản hồi được", 0)
        return None, ""

    await _emit(ws, "xanax", "text", content=response)
    await add_pipeline_log(session_id, "xanax", "text", response, 0)

    plan = _extract_json(response)
    if not plan or "todos_for_codex" not in plan:
        msg = "Không parse được kế hoạch từ Xanax — format JSON lỗi"
        await _emit(ws, "xanax", "error", content=msg)
        await add_pipeline_log(session_id, "xanax", "error", msg, 1)
        return None, response

    await _emit(ws, "xanax", "done")
    return plan, response


async def _step_claude(
    ws: WebSocket, plan: dict, workdir: str, session_id: int
) -> tuple[bool, str]:
    await _emit(ws, "pipeline", "step", step=2, content="Claude đang lên kế hoạch chi tiết...")
    await _emit(ws, "claude", "status", content="running")

    plan_text = plan.get("plan_for_claude", "")
    todos     = plan.get("todos_for_codex", [])
    todos_str = "\n".join(f"- {t}" for t in todos)

    prompt = f"""Bạn là một technical planner. Xanax (AI coordinator) đã giao cho bạn nhiệm vụ sau:

## Kế hoạch từ Xanax
{plan_text}

## Todo list cho Codex
{todos_str}

## Thư mục làm việc
{workdir}

Nhiệm vụ của bạn:
1. Xem xét kế hoạch và bổ sung chi tiết kỹ thuật còn thiếu
2. Làm rõ từng todo: file nào cần chỉnh, hàm nào cần thêm/sửa, logic cụ thể ra sao
3. Xác định các dependency và thứ tự thực hiện đúng
4. Viết lại todo list đã được làm rõ để chuyển cho Codex thực thi

Hãy cụ thể và kỹ thuật — Codex sẽ đọc output này để thực thi code trực tiếp."""

    collected: list[str] = []
    ok = True
    seq = 0

    async for event in claude_runner.run(prompt, cwd=workdir):
        t = event["type"]
        c = event.get("content", "")
        if t == "done":
            ok = event.get("ok", True)
        else:
            await _emit(ws, "claude", t, content=c)
            if t in ("text", "tool", "shell", "output", "file", "error") and c:
                await add_pipeline_log(session_id, "claude", t, c, seq)
                seq += 1
            if t == "text":
                collected.append(c)
            elif t == "error":
                ok = False

    if ok:
        await _emit(ws, "claude", "done")
    return ok, "".join(collected)


async def _step_codex(
    ws: WebSocket, plan: dict, claude_notes: str, workdir: str, session_id: int
) -> tuple[bool, str]:
    await _emit(ws, "pipeline", "step", step=3, content="Codex đang thực thi code...")
    await _emit(ws, "codex", "status", content="running")

    todos     = plan.get("todos_for_codex", [])
    todos_str = "\n".join(f"{i+1}. {t}" for i, t in enumerate(todos))

    prompt = f"""Thực hiện các nhiệm vụ sau trong thư mục {workdir}:

## Todo list
{todos_str}

## Hướng dẫn chi tiết từ Claude
{claude_notes}

Hãy thực thi từng bước, đọc file hiện có trước khi sửa, và đảm bảo code hoạt động đúng."""

    collected: list[str] = []
    ok = True
    seq = 0
    async for event in codex_runner.run(prompt, cwd=workdir):
        t = event["type"]
        c = event.get("content", "")
        if t == "done":
            ok = event.get("ok", True)
        else:
            await _emit(ws, "codex", t, content=c)
            if t in ("text", "tool", "shell", "output", "file", "error") and c:
                await add_pipeline_log(session_id, "codex", t, c, seq)
                seq += 1
            if t in ("text", "shell", "output"):
                collected.append(c)
            elif t == "error":
                ok = False

    if ok:
        await _emit(ws, "codex", "done")
    return ok, "".join(collected)


# ── Main pipeline coroutine ───────────────────────────────────────────────────

async def _run_pipeline(
    ws: WebSocket,
    session_id: int,
    task: str,
    workdir: str,
    agents: list[str],
    review_mode: bool,
) -> None:
    """Full pipeline: Xanax → Claude → Codex, with optional human-in-the-loop."""
    xanax_out = ""
    claude_out = ""
    codex_out  = ""
    plan: dict = {"plan_for_claude": task, "todos_for_codex": [task]}

    try:
        # ── Step 1: Xanax ─────────────────────────────────────────────────
        if "xanax" in agents:
            for attempt in range(2):
                if attempt:
                    await _emit(ws, "pipeline", "retrying",
                                content="⟳ Xanax gặp lỗi — đang thử lại...")
                    await asyncio.sleep(3)
                plan, xanax_out = await _step_xanax(ws, task, workdir, session_id)
                if plan:
                    break

            if not plan:
                await update_task_session(session_id, xanax_output=xanax_out)
                await _emit(ws, "pipeline", "error", session_id=session_id,
                            content="Xanax không tạo được kế hoạch — pipeline dừng.")
                return

            # Save plan to DB immediately (enables rerun even if pipeline aborts later)
            await update_task_session(
                session_id,
                xanax_output=xanax_out,
                xanax_plan_json=json.dumps(plan, ensure_ascii=False),
            )

            # Human-in-the-loop: review Xanax plan before Claude
            if review_mode and "claude" in agents:
                await _emit(ws, "pipeline", "plan_ready",
                            content=json.dumps(plan, ensure_ascii=False),
                            session_id=session_id)
                approved = await _wait_approval(session_id)
                if approved.get("abort"):
                    await _emit(ws, "pipeline", "error", session_id=session_id,
                                content="Pipeline bị huỷ.")
                    return
                # Apply user edits to plan if provided
                edited_plan = approved.get("plan")
                if edited_plan and isinstance(edited_plan, dict):
                    plan.update(edited_plan)
                    await update_task_session(
                        session_id,
                        xanax_plan_json=json.dumps(plan, ensure_ascii=False),
                    )
        else:
            await _emit(ws, "pipeline", "step", step=1, content="Bỏ qua Xanax")
            await _emit(ws, "xanax", "done")

        # ── Step 2: Claude ────────────────────────────────────────────────
        if "claude" in agents:
            claude_ok = False
            for attempt in range(2):
                if attempt:
                    await _emit(ws, "pipeline", "retrying",
                                content="⟳ Claude gặp lỗi — đang thử lại...")
                    await asyncio.sleep(3)
                claude_ok, claude_out = await _step_claude(ws, plan, workdir, session_id)
                if claude_ok:
                    break

            if not claude_ok:
                await update_task_session(session_id, claude_output=claude_out)
                await _emit(ws, "pipeline", "error", session_id=session_id,
                            content="Claude CLI thất bại — pipeline dừng.")
                return

            # Human-in-the-loop: review Claude plan before Codex
            if review_mode and "codex" in agents:
                await _emit(ws, "pipeline", "todos_ready",
                            content=claude_out, session_id=session_id)
                approved = await _wait_approval(session_id)
                if approved.get("abort"):
                    await update_task_session(session_id, claude_output=claude_out)
                    await _emit(ws, "pipeline", "error", session_id=session_id,
                                content="Pipeline bị huỷ.")
                    return
        else:
            await _emit(ws, "pipeline", "step", step=2, content="Bỏ qua Claude")
            await _emit(ws, "claude", "done")

        # ── Step 3: Codex ─────────────────────────────────────────────────
        if "codex" in agents:
            codex_ok = False
            for attempt in range(2):
                if attempt:
                    await _emit(ws, "pipeline", "retrying",
                                content="⟳ Codex gặp lỗi — đang thử lại...")
                    await asyncio.sleep(3)
                codex_ok, codex_out = await _step_codex(
                    ws, plan, claude_out, workdir, session_id
                )
                if codex_ok:
                    break

            await update_task_session(
                session_id,
                claude_output=claude_out,
                codex_output=codex_out,
            )

            if not codex_ok:
                await _emit(ws, "pipeline", "error", session_id=session_id,
                            content="Codex CLI thất bại — pipeline dừng.")
                return
        else:
            await _emit(ws, "pipeline", "step", step=3, content="Bỏ qua Codex")
            await _emit(ws, "codex", "done")
            await update_task_session(session_id, claude_output=claude_out)

        await _emit(ws, "pipeline", "done", session_id=session_id,
                    content="Tất cả agents đã hoàn thành nhiệm vụ.")

    except Exception as e:
        logger.exception("Pipeline error for session %s", session_id)
        await update_task_session(session_id, status="in_progress")
        await _emit(ws, "pipeline", "error", session_id=session_id, content=str(e))


# ── Rerun from specific step ──────────────────────────────────────────────────

async def _handle_rerun(ws: WebSocket, session_id: int, from_step: int) -> None:
    """
    Rerun pipeline from a specific step using saved outputs.
    from_step=2: rerun Claude + Codex (uses saved xanax_plan_json)
    from_step=3: rerun Codex only   (uses saved claude_output)
    """
    try:
        session = await get_task_session(session_id)
        if not session:
            await _emit(ws, "pipeline", "error", content="Task session not found")
            return

        workdir          = session.get("workdir") or _DEFAULT_WORKDIR
        xanax_plan_json  = session.get("xanax_plan_json", "")
        saved_claude_out = session.get("claude_output", "")

        plan = None
        if xanax_plan_json:
            try:
                plan = json.loads(xanax_plan_json)
            except json.JSONDecodeError:
                pass

        # Clear logs for agents being rerun
        if from_step <= 2:
            await delete_agent_pipeline_logs(session_id, "claude")
            await delete_agent_pipeline_logs(session_id, "codex")
        else:
            await delete_agent_pipeline_logs(session_id, "codex")

        # Reset session status
        await update_task_session(session_id, status="in_progress")

        if from_step <= 2:
            if not plan:
                await _emit(ws, "pipeline", "error",
                            content="Không có kế hoạch Xanax để rerun từ Claude.")
                return

            claude_ok, claude_out = await _step_claude(ws, plan, workdir, session_id)
            if not claude_ok:
                await update_task_session(session_id, claude_output=claude_out)
                await _emit(ws, "pipeline", "error", session_id=session_id,
                            content="Claude CLI thất bại.")
                return

            codex_ok, codex_out = await _step_codex(ws, plan, claude_out, workdir, session_id)
            await update_task_session(
                session_id, claude_output=claude_out, codex_output=codex_out
            )
            if not codex_ok:
                await _emit(ws, "pipeline", "error", session_id=session_id,
                            content="Codex CLI thất bại.")
                return

        else:  # from_step == 3
            if not plan:
                await _emit(ws, "pipeline", "error",
                            content="Không có kế hoạch để rerun Codex.")
                return

            codex_ok, codex_out = await _step_codex(
                ws, plan, saved_claude_out, workdir, session_id
            )
            await update_task_session(session_id, codex_output=codex_out)
            if not codex_ok:
                await _emit(ws, "pipeline", "error", session_id=session_id,
                            content="Codex CLI thất bại.")
                return

        await _emit(ws, "pipeline", "done", session_id=session_id,
                    content="Rerun hoàn thành.")

    except Exception as e:
        logger.exception("Rerun error for session %s", session_id)
        await _emit(ws, "pipeline", "error", session_id=session_id, content=str(e))


# ── Pass/Fail/Summarise handlers (unchanged) ──────────────────────────────────

async def _handle_pass(session_id: int, ws: WebSocket) -> None:
    try:
        await update_task_session(session_id, status="pass")
        await _emit(ws, "pipeline", "verdict_set", content="pass")
    except Exception:
        logger.exception("_handle_pass failed for task session %s", session_id)
        await _emit(ws, "pipeline", "error", content="Lỗi khi đánh dấu Pass")


async def _handle_summarise(session_id: int, feedback: str, ws: WebSocket) -> None:
    try:
        session = await get_task_session(session_id)
        if not session:
            await _emit(ws, "pipeline", "error", content="Task session not found")
            return

        soul       = _read_soul()
        title      = session["title"]
        task       = session["task_description"]
        xanax_out  = session["xanax_output"]
        claude_out = session["claude_output"]
        codex_out  = session["codex_output"]
        status     = session.get("status", "pass")

        if feedback:
            prompt = (
                f'Task runner session "{title}" (status: {status}).\n\n'
                f'Nhiệm vụ: {task}\n\nKế hoạch Xanax:\n{xanax_out}\n\n'
                f'Claude đã làm rõ:\n{claude_out}\n\nCodex đã thực thi:\n{codex_out}\n\n'
                f'Papa muốn đúc kết với trọng tâm: **{feedback}**\n\n'
                "Hãy đúc kết dựa trên trọng tâm đó — cách tiếp cận, kỹ thuật hay, "
                "bài học áp dụng cho task tương tự. Viết ngắn gọn, súc tích, gạch đầu dòng."
            )
        else:
            prompt = (
                f'Task runner session "{title}" đã được Papa đánh dấu {status.upper()}.\n\n'
                f'Nhiệm vụ: {task}\n\nKế hoạch Xanax:\n{xanax_out}\n\n'
                f'Claude đã làm rõ:\n{claude_out}\n\nCodex đã thực thi:\n{codex_out}\n\n'
                "Hãy đúc kết những điều quan trọng từ task này: cách tiếp cận hiệu quả, "
                "kỹ thuật hay, bài học để áp dụng cho task tương tự sau này. "
                "Viết ngắn gọn, súc tích, dùng gạch đầu dòng."
            )

        messages: list[dict] = []
        if soul:
            messages.append({"role": "system", "content": soul})
        messages.append({"role": "user", "content": prompt})

        summary = await hermes.complete_with_context(messages)
        if not summary:
            await _emit(ws, "pipeline", "error", content="Không tạo được đúc kết")
            return

        await update_task_session(session_id, result_notes=summary)
        await _emit(ws, "pipeline", "notes_preview", content=summary)

    except Exception:
        logger.exception("_handle_summarise failed for task session %s", session_id)
        await _emit(ws, "pipeline", "error", content="Đúc kết thất bại")


async def _handle_confirm_notes(session_id: int, content: str, ws: WebSocket) -> None:
    try:
        session = await get_task_session(session_id)
        if not session:
            await _emit(ws, "pipeline", "error", content="Task session not found")
            return
        _upsert_soul_task(session_id, session["title"], content)
        await _emit(ws, "pipeline", "notes_saved")
    except Exception:
        logger.exception("_handle_confirm_notes failed for task session %s", session_id)
        await _emit(ws, "pipeline", "error", content="Lỗi khi lưu vào SOUL.md")


async def _handle_fail(session_id: int, ws: WebSocket) -> None:
    try:
        session = await get_task_session(session_id)
        if not session:
            await _emit(ws, "pipeline", "error", content="Task session not found")
            return

        soul = _read_soul()
        prompt = (
            f'Task runner session "{session["title"]}" đã được Papa đánh dấu FAIL.\n\n'
            f'Nhiệm vụ: {session["task_description"]}\n\n'
            f'Kế hoạch Xanax:\n{session["xanax_output"]}\n\n'
            f'Claude làm rõ:\n{session["claude_output"]}\n\n'
            f'Codex thực thi:\n{session["codex_output"]}\n\n'
            "Hãy phân tích:\n"
            "1. Pipeline gặp vấn đề gì? Bước nào thất bại và tại sao?\n"
            "2. Cần cải thiện điều gì để task tương tự sẽ thành công?\n"
            "Viết ngắn gọn, súc tích, dùng gạch đầu dòng."
        )

        messages: list[dict] = []
        if soul:
            messages.append({"role": "system", "content": soul})
        messages.append({"role": "user", "content": prompt})

        analysis = await hermes.complete_with_context(messages)
        if not analysis:
            return

        await update_task_session(session_id, status="fail", failure_notes=analysis)
        await _emit(ws, "pipeline", "failure_analysed", content=analysis)

    except Exception:
        logger.exception("_handle_fail failed for task session %s", session_id)
        await _emit(ws, "pipeline", "error", content="Phân tích thất bại")


# ── WebSocket handler ─────────────────────────────────────────────────────────

@router.websocket("/ws/task")
async def websocket_task(websocket: WebSocket):
    await websocket.accept()
    logger.info("Task WebSocket connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await _emit(websocket, "pipeline", "error", content="Invalid JSON")
                continue

            action = data.get("action")

            # ── Human-in-the-loop approvals ───────────────────────────────
            if action in ("approve_plan", "approve_todos"):
                session_id = data.get("session_id")
                if session_id:
                    _signal_approval(int(session_id), data)
                continue

            # ── Rerun actions ─────────────────────────────────────────────
            if action == "rerun_from_claude":
                sid = data.get("session_id")
                if sid:
                    asyncio.create_task(_handle_rerun(websocket, int(sid), from_step=2))
                continue

            if action == "rerun_from_codex":
                sid = data.get("session_id")
                if sid:
                    asyncio.create_task(_handle_rerun(websocket, int(sid), from_step=3))
                continue

            # ── Pass / Fail / Summarise ───────────────────────────────────
            if action in ("pass", "fail", "summarise", "confirm_notes", "improve_from_fail"):
                session_id = data.get("session_id")
                if not session_id:
                    await _emit(websocket, "pipeline", "error", content="Missing session_id")
                    continue
                sid = int(session_id)
                if action == "pass":
                    asyncio.create_task(_handle_pass(sid, websocket))
                elif action == "fail":
                    asyncio.create_task(_handle_fail(sid, websocket))
                elif action == "confirm_notes":
                    asyncio.create_task(
                        _handle_confirm_notes(sid, data.get("content", "").strip(), websocket)
                    )
                else:
                    asyncio.create_task(
                        _handle_summarise(sid, data.get("feedback", "").strip(), websocket)
                    )
                continue

            # ── Run new pipeline ──────────────────────────────────────────
            task    = data.get("task", "").strip()
            workdir = data.get("workdir", "").strip() or _DEFAULT_WORKDIR
            agents  = data.get("agents", ["xanax", "claude", "codex"])
            review_mode = bool(data.get("review_mode", False))

            if not task:
                await _emit(websocket, "pipeline", "error", content="Nhiệm vụ trống")
                continue

            title      = _make_title(task)
            session_id = await create_task_session(title, task, workdir)
            await _emit(websocket, "pipeline", "session_created", session_id=session_id)

            asyncio.create_task(
                _run_pipeline(websocket, session_id, task, workdir, agents, review_mode)
            )

    except WebSocketDisconnect:
        logger.info("Task WebSocket disconnected")
    except Exception as e:
        logger.exception("Task WebSocket outer error")
        try:
            await _emit(websocket, "pipeline", "error", content=str(e))
        except Exception:
            pass
