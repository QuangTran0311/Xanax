"""
Training WebSocket — streams Xanax responses.
Summarise chỉ xảy ra khi Papa bấm Pass hoặc Fail (không tự động sau mỗi tin nhắn).

Protocol:
  Client → Server:
    { "training_session_id": 1, "message": "..." }          -- chat message
    { "action": "summarise_pass", "session_id": 1 }         -- pass → đúc kết → SOUL.md
    { "action": "summarise_fail", "session_id": 1 }         -- fail → phân tích thất bại

  Server → Client:
    { "type": "status",           "status": "thinking" }
    { "type": "chunk",            "content": "..." }
    { "type": "done" }
    { "type": "notes_updated",    "content": "<summary>" }  -- pass: SOUL.md cập nhật
    { "type": "failure_analysed", "content": "<analysis>" } -- fail: phân tích thất bại
    { "type": "error",            "message": "..." }
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

from core.hermes_bridge import hermes
from hub.database import (
    add_training_message,
    get_training_messages,
    get_training_session,
    update_training_session,
    get_agent_config,
    list_agent_configs,
    list_skills,
    list_projects,
    list_work_items,
    list_workflow_tasks,
    list_model_pool,
    create_xanax_note,
    list_xanax_notes,
    delete_xanax_note,
    create_work_item,
    update_work_item,
)

logger = logging.getLogger("xanax.ws.training")
router = APIRouter()


# ── Buổi dạy có học viên ──────────────────────────────────────────────────────

async def _stream_student(ws: WebSocket, agent: dict, history: list[dict]) -> str:
    """Chính nhân viên học viên trả lời, bằng model và soul của nó.

    Tách khỏi `_stream_agent` của phòng họp dù cùng ý tưởng, vì luật hai nơi
    khác nhau: ở đây không có nhân viên khác để lẫn vai, không có định dạng
    "[Tên]: " cần gỡ, và quan trọng nhất là học viên KHÔNG được cầm công cụ.

    Không truyền `tools` và không phân tích [[XANAX:...]] cho học viên. Bộ công
    cụ trong file này (save_note, create_work_item, trigger_workflow...) là
    quyền của Xanax; đưa cho một học viên đang được dạy nghĩa là một câu dạy
    thử có thể tạo việc thật hoặc chạy quy trình thật.
    """
    from core.agent_soul import read_soul, sync_agent_soul

    persona = (agent.get("system_prompt") or "").strip() or (
        f"Bạn là {agent.get('name')}, {agent.get('role') or 'nhân viên AI'}."
    )
    await sync_agent_soul(agent)
    soul_content = read_soul(agent["id"])

    system_prompt = "\n\n".join(filter(None, [
        persona,
        soul_content,
        f"BỐI CẢNH: bạn LÀ {agent.get('name')} ({agent.get('role') or 'nhân viên AI'}), "
        "đang trong một buổi học riêng. Người nói chuyện với bạn là Papa — người "
        "trực tiếp dạy bạn. Hãy trả lời với tư cách chính bạn, ngôi thứ nhất.\n"
        "- Papa dạy điều gì thì nói lại BẰNG LỜI CỦA BẠN để Papa biết bạn hiểu đúng "
        "hay chưa; hiểu sai còn sửa được, gật đầu cho qua thì sai sẽ đi vào soul.\n"
        "- Chỗ nào chưa rõ thì HỎI LẠI, đừng đoán. Đây là lúc để hỏi.\n"
        "- KHÔNG bịa là mình đã làm hay đã chạy bất cứ thứ gì. Trong buổi học bạn "
        "không có công cụ nào và không thực hiện việc thật.",
    ]))

    await _send(ws, {"type": "status", "status": "thinking"})

    llm_messages = [{"role": "system", "content": system_prompt}]
    for m in history:
        llm_messages.append({"role": m["role"], "content": m["content"]})

    try:
        model_pool_ids: list[int] = json.loads(agent.get("model_pool_ids_json") or "[]")
    except Exception:
        model_pool_ids = []

    full = ""
    if model_pool_ids:
        # Dùng đúng danh sách model ưu tiên đã cấu hình cho nhân viên, tự fallback
        # khi model đầu hỏng — giống phòng họp và quy trình.
        from core.model_pool_bridge import stream_from_agent_models
        async for delta in stream_from_agent_models(model_pool_ids, llm_messages):
            if ws.client_state != WebSocketState.CONNECTED:
                break
            full += delta
            await _send(ws, {"type": "chunk", "content": delta})
    else:
        async for delta in hermes.stream_with_context(llm_messages):
            if ws.client_state != WebSocketState.CONNECTED:
                break
            full += delta
            await _send(ws, {"type": "chunk", "content": delta})
    return full


# ── Live DB context ───────────────────────────────────────────────────────────

async def _build_live_context() -> str:
    """Build a fresh snapshot of Xanax DB data to inject into every chat prompt."""
    import json as _json
    lines = ["**[DỮ LIỆU THỰC TẾ XANAX — cập nhật real-time mỗi tin nhắn]**\n"]

    agents = await list_agent_configs()
    skills_all = await list_skills()
    skill_map = {s["id"]: s["name"] for s in skills_all}

    lines.append("Nhân viên:")
    for a in agents:
        try:
            skill_ids = _json.loads(a.get("skills_json") or "[]")
            skill_names = [skill_map.get(i, str(i)) for i in skill_ids]
        except Exception:
            skill_names = []
        enabled = "✓" if a.get("enabled", 1) else "✗"
        lines.append(f"- [{enabled}] {a['name']} | {a['role']} | model: {a.get('model','')} | skills: {', '.join(skill_names) or 'không có'}")

    lines.append("\nKỹ năng:")
    for s in skills_all:
        enabled = "✓" if s.get("enabled", 1) else "✗"
        lines.append(f"- [{enabled}] {s['name']} — {s.get('description','')}")

    projects = await list_projects()
    project_map = {p["id"]: p["name"] for p in projects}
    lines.append("\nDự án:")
    for p in projects:
        lines.append(f"- [{p['status']}] {p['name']} — {(p.get('description') or '')[:80]}")

    lines.append("\nCông việc:")
    added_items = False
    for p in projects:
        items = await list_work_items(p["id"])
        for i in items:
            lines.append(f"- [{i['status']}] {i['title']} (dự án: {p['name']}, priority: {i.get('priority','')})")
            added_items = True
    if not added_items:
        lines.append("- (chưa có)")

    # Tách quy trình (kind=company) và tác vụ (kind=automation): hai loại khác nhau
    # và có thể trùng tên, gộp chung một danh sách thì không phân biệt được cái nào.
    workflows = await list_workflow_tasks()
    for kind, title in (
        ("company", "Quy trình (luồng phối hợp nhiều bước, thường gọi các tác vụ con)"),
        ("automation", "Tác vụ (một việc tự động đơn lẻ)"),
    ):
        rows = [w for w in workflows if (w.get("kind") or "automation") == kind]
        lines.append(f"\n{title}:")
        if not rows:
            lines.append("- (chưa có)")
        for w in rows:
            pname = project_map.get(w.get("project_id"), "?")
            lines.append(
                f"- id={w['id']} {w['name']} — {w.get('description','')} "
                f"(dự án: {pname}, trạng thái: {w.get('status','')})"
            )

    model_pool = await list_model_pool()
    lines.append("\nModel Pool:")
    for m in model_pool:
        enabled = "✓" if m.get("enabled", 1) else "✗"
        lines.append(f"- [{enabled}] ID={m['id']} {m['name']} | provider: {m.get('provider','')} | model_id: {m.get('model_id','')} | category: {m.get('category','')}")

    notes = await list_xanax_notes()
    if notes:
        lines.append("\nGhi nhớ của Xanax (bền vững giữa các session):")
        for n in notes:
            lines.append(f"- [Note #{n['id']}] {n['content']}")

    lines.append("\nKhi Papa hỏi về dữ liệu công ty → dùng thông tin trên, không suy đoán.")
    lines.append("""
---
## Hành động Xanax có thể thực hiện

Khi Papa yêu cầu thực hiện hành động, nhúng lệnh vào CUỐI response (sau nội dung trả lời):
[[XANAX:action|param1=value1|param2=value2]]

Hành động hỗ trợ:
- [[XANAX:save_note|content=Nội dung cần ghi nhớ lâu dài]] — Lưu ghi nhớ bền vững qua các session
- [[XANAX:delete_note|id=3]] — Xóa ghi nhớ cũ theo ID
- [[XANAX:create_work_item|project_id=1|title=Tên công việc|description=...|priority=high|assignee=Tên Agent]] — Tạo công việc mới trong dự án
- [[XANAX:update_work_item|id=5|status=in_progress|assignee=Tên Agent]] — Cập nhật trạng thái/người phụ trách
- [[XANAX:trigger_workflow|task_id=2|input=Chủ đề/nội dung cho lần chạy này]] — Kích hoạt quy trình tự động.
  input là chủ đề truyền vào node Bắt đầu; nếu Papa chưa nói rõ chủ đề thì hỏi lại, đừng tự bịa.

Quy tắc:
- Chỉ dùng khi Papa yêu cầu hành động cụ thể, KHÔNG tự ý thực hiện
- Dùng đúng ID thật từ dữ liệu phía trên (project_id, task_id, agent name)
- priority: low / medium / high / urgent | status: backlog / todo / in_progress / done
- Lệnh sẽ được thực thi tự động và Papa thấy kết quả — không cần giải thích lại lệnh""")
    return "\n".join(lines)


# ── Tool call execution ───────────────────────────────────────────────────────

_TOOL_RE = re.compile(r'\[\[XANAX:([^\]]+)\]\]')


def _parse_tool_calls(text: str) -> list[dict]:
    calls = []
    for m in _TOOL_RE.finditer(text):
        parts = m.group(1).split('|')
        action = parts[0].strip()
        params: dict[str, str] = {}
        for p in parts[1:]:
            if '=' in p:
                k, v = p.split('=', 1)
                params[k.strip()] = v.strip()
        calls.append({'action': action, 'params': params})
    return calls


async def _execute_tool_call(call: dict) -> dict:
    action = call['action']
    params = call['params']
    try:
        if action == 'save_note':
            content = params.get('content', '').strip()
            if not content:
                return {'ok': False, 'action': action, 'error': 'content là bắt buộc'}
            note_id = await create_xanax_note(content)
            return {'ok': True, 'action': action, 'message': f'Đã lưu ghi nhớ #{note_id}'}

        elif action == 'delete_note':
            try:
                note_id = int(params.get('id', 0))
            except ValueError:
                return {'ok': False, 'action': action, 'error': 'id không hợp lệ'}
            ok = await delete_xanax_note(note_id)
            return {'ok': ok, 'action': action,
                    'message': f'Đã xóa ghi nhớ #{note_id}' if ok else f'Không tìm thấy ghi nhớ #{note_id}'}

        elif action == 'create_work_item':
            try:
                project_id = int(params.get('project_id', 0))
            except ValueError:
                project_id = 0
            title = params.get('title', '').strip()
            if not project_id or not title:
                return {'ok': False, 'action': action, 'error': 'project_id và title là bắt buộc'}
            description = params.get('description', '')
            priority = params.get('priority', 'medium')
            assigned_agent_id = None
            assignee = params.get('assignee', '').strip()
            if assignee:
                agents = await list_agent_configs()
                for a in agents:
                    if a['name'].lower() == assignee.lower() or str(a['id']) == assignee:
                        assigned_agent_id = a['id']
                        break
            item_id = await create_work_item(project_id, title, description, 'backlog', priority, assigned_agent_id)
            return {'ok': True, 'action': action, 'message': f'Đã tạo công việc #{item_id}: "{title}"'}

        elif action == 'update_work_item':
            try:
                item_id = int(params.get('id', 0))
            except ValueError:
                item_id = 0
            if not item_id:
                return {'ok': False, 'action': action, 'error': 'id là bắt buộc'}
            kwargs: dict = {}
            for k in ('status', 'priority', 'title', 'description'):
                if k in params:
                    kwargs[k] = params[k]
            if 'assignee' in params:
                agents = await list_agent_configs()
                for a in agents:
                    if a['name'].lower() == params['assignee'].lower() or str(a['id']) == params['assignee']:
                        kwargs['assigned_agent_id'] = a['id']
                        break
            ok = await update_work_item(item_id, **kwargs)
            return {'ok': ok, 'action': action,
                    'message': f'Đã cập nhật công việc #{item_id}' if ok else f'Không tìm thấy công việc #{item_id}'}

        elif action == 'trigger_workflow':
            try:
                task_id = int(params.get('task_id', 0))
            except ValueError:
                task_id = 0
            if not task_id:
                return {'ok': False, 'action': action, 'error': 'task_id là bắt buộc'}
            # Chủ đề đi kèm: quy trình nhận nó qua node Bắt đầu. Thiếu tham số này
            # thì quy trình chạy với đầu vào rỗng và nội dung do AI tự bịa.
            topic = str(params.get('input') or '').strip()
            from api.websocket_workflow import execute_workflow_headless
            asyncio.create_task(execute_workflow_headless(
                task_id, user_input=topic, triggered_by='chat',
            ))
            return {
                'ok': True, 'action': action,
                'message': f'Đã kích hoạt quy trình #{task_id}'
                           + (f' với chủ đề: "{topic}"' if topic else ' (không có chủ đề)'),
            }

        else:
            return {'ok': False, 'action': action, 'error': f'Hành động không hỗ trợ: {action}'}

    except Exception as e:
        logger.exception("Tool call failed: %s", action)
        return {'ok': False, 'action': action, 'error': str(e)}


# ── SOUL.md helpers ───────────────────────────────────────────────────────────

def _soul_path() -> Path:
    local_app_data = (
        os.environ.get("LOCALAPPDATA")
        or os.path.expandvars("%LOCALAPPDATA%")
        or str(Path.home() / "AppData" / "Local")
    )
    return Path(local_app_data) / "hermes" / "SOUL.md"


def _read_soul() -> str:
    p = _soul_path()
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _upsert_soul_note(session_id: int, session_title: str, content: str) -> None:
    """Insert or replace the tagged block for this session in SOUL.md."""
    p = _soul_path()
    if not p.exists():
        logger.warning("SOUL.md not found at %s — skipping upsert", p)
        return

    start_tag = f"<!-- SESSION:{session_id} -->"
    end_tag   = f"<!-- /SESSION:{session_id} -->"
    block     = f"{start_tag}\n**{session_title}**\n{content.strip()}\n{end_tag}"

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
            updated = current.rstrip() + f"\n\n{marker}\n{block}\n"

    p.write_text(updated, encoding="utf-8")
    logger.info("SOUL.md upserted for session %s at %s", session_id, p)


# ── Summarise on Pass ─────────────────────────────────────────────────────────

async def _summarise_pass(
    session_id: int,
    session_title: str,
    history: list[dict],
    ws: WebSocket,
) -> None:
    """
    Papa bấm Pass → đúc kết hội thoại, upsert vào SOUL.md, thông báo client.
    """
    try:
        convo_lines = [
            f"{'Papa' if m['role'] == 'user' else 'Xanax'}: {m['content']}"
            for m in history
            if m["role"] in ("user", "assistant")
        ]
        if not convo_lines:
            return

        convo = "\n".join(convo_lines)
        soul  = _read_soul()
        live_context = await _build_live_context()
        system_content = "\n\n".join(filter(None, [soul, live_context]))

        prompt = (
            f'Dưới đây là đoạn hội thoại training giữa Papa và Xanax '
            f'về chủ đề "{session_title}":\n\n'
            f"{convo}\n\n"
            "Hãy đúc kết thành các điều quan trọng Xanax đã học hoặc được nhắc nhở "
            "trong session này. Viết ngắn gọn, súc tích, dùng gạch đầu dòng. "
            "Chỉ trả lời phần đúc kết, không thêm lời dẫn hay giải thích."
        )

        messages: list[dict] = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": prompt})

        summary = await hermes.complete_with_context(messages)
        if not summary:
            return

        await update_training_session(session_id, result_notes=summary)
        _upsert_soul_note(session_id, session_title, summary)

        await _send(ws, {"type": "notes_updated", "content": summary})
        logger.info("Pass summary complete for session %s", session_id)

    except Exception:
        logger.exception("_summarise_pass failed for session %s", session_id)
        await _send(ws, {"type": "error", "message": "Đúc kết thất bại"})


# ── Analyse on Fail ───────────────────────────────────────────────────────────

async def _analyse_fail(
    session_id: int,
    session_title: str,
    history: list[dict],
    ws: WebSocket,
) -> None:
    """
    Papa bấm Fail → phân tích điểm chưa ổn, lưu vào result_notes.
    KHÔNG cập nhật SOUL.md — đây là bài học từ thất bại để cải thiện sau.
    """
    try:
        convo_lines = [
            f"{'Papa' if m['role'] == 'user' else 'Xanax'}: {m['content']}"
            for m in history
            if m["role"] in ("user", "assistant")
        ]
        if not convo_lines:
            return

        convo = "\n".join(convo_lines)
        soul  = _read_soul()
        live_context = await _build_live_context()
        system_content = "\n\n".join(filter(None, [soul, live_context]))

        prompt = (
            f'Session training "{session_title}" đã được đánh dấu là FAIL.\n\n'
            f'Hội thoại:\n{convo}\n\n'
            "Hãy phân tích:\n"
            "1. Xanax đã làm gì chưa đúng hoặc chưa đủ trong session này?\n"
            "2. Cần cải thiện điều gì để session tương tự sẽ đạt Pass?\n"
            "Viết ngắn gọn, súc tích, dùng gạch đầu dòng. "
            "Chỉ trả lời phần phân tích, không thêm lời dẫn."
        )

        messages: list[dict] = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": prompt})

        analysis = await hermes.complete_with_context(messages)
        if not analysis:
            return

        await update_training_session(session_id, result_notes=analysis)

        await _send(ws, {"type": "failure_analysed", "content": analysis})
        logger.info("Fail analysis complete for session %s", session_id)

    except Exception:
        logger.exception("_analyse_fail failed for session %s", session_id)
        await _send(ws, {"type": "error", "message": "Phân tích thất bại"})


# ── Improve from fail feedback ────────────────────────────────────────────────

async def _improve_from_fail(
    session_id: int,
    session_title: str,
    feedback: str,
    ws: WebSocket,
) -> None:
    """
    Papa góp ý sau khi fail → Xanax đúc kết từ fail + góp ý → upsert vào SOUL.md.
    """
    try:
        session = await get_training_session(session_id)
        if not session:
            return

        soul          = _read_soul()
        live_context  = await _build_live_context()
        system_content = "\n\n".join(filter(None, [soul, live_context]))
        prev_analysis = session.get("result_notes", "")

        prompt = (
            f'Session training "{session_title}" đã fail. '
            f'Phân tích trước đó:\n{prev_analysis}\n\n'
            f'Papa góp ý thêm:\n{feedback}\n\n'
            "Dựa vào cả phân tích và góp ý của Papa, hãy đúc kết thành các điều "
            "Xanax cần ghi nhớ và cải thiện để hoàn thiện bản thân. "
            "Viết ngắn gọn, súc tích, dùng gạch đầu dòng. "
            "Chỉ trả lời phần đúc kết, không thêm lời dẫn."
        )

        messages: list[dict] = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": prompt})

        improvement = await hermes.complete_with_context(messages)
        if not improvement:
            return

        await update_training_session(session_id, result_notes=improvement)
        _upsert_soul_note(session_id, session_title, improvement)

        await _send(ws, {"type": "notes_updated", "content": improvement})
        logger.info("Improve-from-fail complete for session %s", session_id)

    except Exception:
        logger.exception("_improve_from_fail failed for session %s", session_id)
        await _send(ws, {"type": "error", "message": "Đúc kết từ góp ý thất bại"})


# ── WebSocket handler ─────────────────────────────────────────────────────────

async def _send(ws: WebSocket, data: dict) -> None:
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


@router.websocket("/ws/training")
async def websocket_training(websocket: WebSocket):
    await websocket.accept()
    logger.info("Training WebSocket connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await _send(websocket, {"type": "error", "message": "Invalid JSON"})
                continue

            # ── Action: pass / fail ───────────────────────────────────────────
            action = data.get("action")
            if action in ("summarise_pass", "summarise_fail", "improve_from_fail"):
                session_id = data.get("session_id")
                if not session_id:
                    await _send(websocket, {"type": "error", "message": "Missing session_id"})
                    continue

                session = await get_training_session(int(session_id))
                if not session:
                    await _send(websocket, {"type": "error", "message": "Session not found"})
                    continue

                if action == "summarise_pass":
                    history = await get_training_messages(int(session_id))
                    await _send(websocket, {"type": "status", "status": "summarising"})
                    asyncio.create_task(
                        _summarise_pass(int(session_id), session["title"], history, websocket)
                    )
                elif action == "summarise_fail":
                    history = await get_training_messages(int(session_id))
                    await _send(websocket, {"type": "status", "status": "analysing"})
                    asyncio.create_task(
                        _analyse_fail(int(session_id), session["title"], history, websocket)
                    )
                else:  # improve_from_fail
                    feedback = data.get("feedback", "").strip()
                    if not feedback:
                        await _send(websocket, {"type": "error", "message": "Góp ý trống"})
                        continue
                    await _send(websocket, {"type": "status", "status": "improving"})
                    asyncio.create_task(
                        _improve_from_fail(int(session_id), session["title"], feedback, websocket)
                    )
                continue

            # ── Chat message ──────────────────────────────────────────────────
            message             = data.get("message", "").strip()
            training_session_id = data.get("training_session_id")

            if not message:
                await _send(websocket, {"type": "error", "message": "Empty message"})
                continue
            if not training_session_id:
                await _send(websocket, {"type": "error", "message": "Missing training_session_id"})
                continue

            session = await get_training_session(int(training_session_id))
            if not session:
                await _send(websocket, {"type": "error", "message": "Training session not found"})
                continue

            # Persist user message
            await add_training_message(int(training_session_id), "user", message)

            # Buổi dạy có học viên: chính nhân viên đó trả lời, bằng model và
            # soul của nó. Không đi qua đường Xanax phía dưới, và đặc biệt không
            # phân tích [[XANAX:...]] — học viên không được cầm công cụ.
            if session.get("agent_id"):
                agent = await get_agent_config(int(session["agent_id"]))
                if not agent:
                    await _send(websocket, {
                        "type": "error",
                        "message": "Học viên của buổi dạy này đã bị xoá khỏi danh sách nhân viên.",
                    })
                    continue
                history = await get_training_messages(int(training_session_id))
                try:
                    reply = await _stream_student(websocket, agent, history)
                    if reply.strip():
                        await add_training_message(
                            int(training_session_id), "assistant", reply.strip()
                        )
                    await _send(websocket, {"type": "done"})
                except Exception as e:
                    logger.exception("Student stream error for session %s", training_session_id)
                    await _send(websocket, {"type": "error", "message": str(e)})
                continue

            # Build context: SOUL.md + live DB snapshot → full history
            soul         = _read_soul()
            live_context = await _build_live_context()
            history      = await get_training_messages(int(training_session_id))

            system_content = "\n\n".join(filter(None, [soul, live_context]))
            messages: list[dict] = []
            if system_content:
                messages.append({"role": "system", "content": system_content})
            for m in history:
                messages.append({"role": m["role"], "content": m["content"]})

            # Stream main response
            await _send(websocket, {"type": "status", "status": "thinking"})
            assistant_chunks: list[str] = []

            try:
                async for chunk in hermes.stream_with_context(messages):
                    if websocket.client_state != WebSocketState.CONNECTED:
                        break
                    await _send(websocket, {"type": "chunk", "content": chunk})
                    assistant_chunks.append(chunk)

                full_response = "".join(assistant_chunks)

                # Execute any embedded tool calls before persisting
                tool_calls = _parse_tool_calls(full_response)
                tool_results: list[dict] = []
                for call in tool_calls:
                    result = await _execute_tool_call(call)
                    tool_results.append(result)
                    logger.info("Tool executed: %s → %s", call['action'], result)

                # Strip [[XANAX:...]] blocks from the stored/displayed text
                clean_response = _TOOL_RE.sub('', full_response).strip()

                if clean_response:
                    await add_training_message(
                        int(training_session_id), "assistant", clean_response
                    )

                if tool_results:
                    await _send(websocket, {"type": "tool_executed",
                                            "clean_text": clean_response,
                                            "results": tool_results})

                await _send(websocket, {"type": "done"})

            except Exception as e:
                logger.exception("Training stream error for session %s", training_session_id)
                await _send(websocket, {"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        logger.info("Training WebSocket disconnected")
    except Exception as e:
        logger.exception("Training WebSocket error")
        try:
            await _send(websocket, {"type": "error", "message": str(e)})
        except Exception:
            pass
