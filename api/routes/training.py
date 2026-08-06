"""
Training session routes — CRUD + SOUL.md update.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hub.database import (
    add_training_message,
    get_agent_config,
    create_training_session,
    delete_training_session,
    get_training_messages,
    get_training_session,
    list_training_sessions,
    update_training_session,
)

logger = logging.getLogger("xanax.training")
router = APIRouter()


def _soul_path() -> Path:
    """Resolve SOUL.md path at call-time — avoids stale import-time env."""
    local_app_data = (
        os.environ.get("LOCALAPPDATA")
        or os.path.expandvars("%LOCALAPPDATA%")
        or str(Path.home() / "AppData" / "Local")
    )
    return Path(local_app_data) / "hermes" / "SOUL.md"


# ── Schemas ────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    title: str
    task_description: str = ""
    # Học viên của buổi dạy — chọn lúc tạo phòng và không đổi về sau. Mỗi phòng
    # đúng MỘT nhân viên. None = dạy chính Xanax (hành vi có từ trước).
    agent_id: int | None = None


class UpdateSessionRequest(BaseModel):
    status: str | None = None          # 'in_progress' | 'pass' | 'fail'
    result_notes: str | None = None
    title: str | None = None
    task_description: str | None = None


class AppendSoulRequest(BaseModel):
    content: str   # text to append under "## Ghi chú từ các session training"


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions():
    return {"sessions": await list_training_sessions()}


@router.post("/sessions", status_code=201)
async def create_session(req: CreateSessionRequest):
    if req.agent_id is not None and not await get_agent_config(req.agent_id):
        raise HTTPException(status_code=400, detail="Không tìm thấy nhân viên được chọn làm học viên")
    sid = await create_training_session(req.title, req.task_description, req.agent_id)
    session = await get_training_session(sid)
    return session


@router.get("/sessions/{session_id}")
async def get_session(session_id: int):
    session = await get_training_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await get_training_messages(session_id)
    return {**session, "messages": messages}


@router.patch("/sessions/{session_id}")
async def update_session(session_id: int, req: UpdateSessionRequest):
    ok = await update_training_session(
        session_id,
        status=req.status,
        result_notes=req.result_notes,
        title=req.title,
        task_description=req.task_description,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return await get_training_session(session_id)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: int):
    ok = await delete_training_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")


# ── Kết thúc buổi dạy: chưng cất → Papa duyệt → ghi vào soul học viên ───────
#
# Cố ý tách làm HAI bước. Nếu vừa tóm tắt vừa ghi thẳng thì không ai kiểm được
# thứ đi vào soul, mà soul ảnh hưởng mọi lần nhân viên làm việc sau đó — một
# bản tóm sai sẽ âm thầm dạy sai mãi. Bản nháp lưu vào DB (lessons_json) chứ
# không giữ trong RAM, để đóng trình duyệt giữa chừng không mất.

_DISTILL_PROMPT = (
    "Bạn đang đọc lại một buổi Papa dạy nhân viên AI tên {name} ({role}).\n\n"
    "Hãy rút ra những BÀI HỌC mà {name} cần nhớ lâu dài, để lần sau làm việc thì "
    "làm đúng ý Papa hơn.\n\n"
    "Quy tắc:\n"
    "- Chỉ lấy điều Papa THỰC SỰ đã dạy trong hội thoại. TUYỆT ĐỐI không suy diễn, "
    "không thêm bài học nghe hay nhưng Papa chưa hề nói.\n"
    "- Mỗi bài học là một câu ngắn, tự đứng một mình đọc vẫn hiểu (đừng viết kiểu "
    "\"như Papa nói ở trên\").\n"
    "- Viết ở dạng chỉ dẫn hành động: nên làm gì / tránh làm gì, chứ không kể lại "
    "diễn biến buổi học.\n"
    "- Nếu buổi học chưa dạy được gì rõ ràng thì trả về mảng RỖNG. Trả mảng rỗng "
    "là câu trả lời hợp lệ và tốt hơn nhiều so với bịa ra bài học.\n\n"
    "Trả lời DUY NHẤT bằng JSON, không thêm chữ nào khác:\n"
    '{{"lessons": ["bài học 1", "bài học 2"]}}'
)

_LESSONS_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_lessons(raw: str) -> list[str]:
    m = _LESSONS_JSON_RE.search(raw or "")
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except Exception:
        return []
    lessons = data.get("lessons")
    # Phải là mảng. Nếu model trả chuỗi thì lặp qua nó sẽ ra từng KÝ TỰ, và soul
    # nhận về một danh sách "bài học" gồm các chữ cái rời.
    if not isinstance(lessons, list):
        return []
    return [str(x).strip() for x in lessons if str(x).strip()]


class SaveLessonsRequest(BaseModel):
    # Danh sách Papa đã xem và sửa. Gửi mảng rỗng = không ghi gì vào soul.
    lessons: list[str]


@router.post("/sessions/{session_id}/distill")
async def distill_lessons(session_id: int):
    """Chưng cất buổi học thành bài học nháp. KHÔNG ghi vào soul."""
    session = await get_training_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("agent_id"):
        raise HTTPException(
            status_code=400,
            detail="Buổi dạy này không có học viên — không có soul nhân viên nào để ghi.",
        )
    agent = await get_agent_config(int(session["agent_id"]))
    if not agent:
        raise HTTPException(status_code=400, detail="Học viên đã bị xoá khỏi danh sách nhân viên")

    messages = await get_training_messages(session_id)
    if not messages:
        return {"lessons": [], "note": "Buổi học chưa có nội dung nào."}

    transcript = "\n".join(
        f"{'Papa' if m['role'] == 'user' else agent['name']}: {m['content']}"
        for m in messages
    )
    system = _DISTILL_PROMPT.format(name=agent["name"], role=agent.get("role") or "nhân viên AI")

    from core.hermes_bridge import hermes
    raw = await hermes.complete_with_context([
        {"role": "system", "content": system},
        {"role": "user", "content": transcript},
    ])
    lessons = _parse_lessons(raw)

    await update_training_session(session_id, lessons_json=json.dumps(lessons, ensure_ascii=False))
    return {"lessons": lessons, "agent_name": agent["name"], "agent_id": agent["id"]}


@router.post("/sessions/{session_id}/lessons")
async def save_lessons(session_id: int, req: SaveLessonsRequest):
    """Ghi bài học Papa ĐÃ DUYỆT vào soul của học viên, rồi đóng buổi dạy."""
    session = await get_training_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("agent_id"):
        raise HTTPException(status_code=400, detail="Buổi dạy này không có học viên")
    agent = await get_agent_config(int(session["agent_id"]))
    if not agent:
        raise HTTPException(status_code=400, detail="Học viên đã bị xoá khỏi danh sách nhân viên")

    lessons = [str(x).strip() for x in (req.lessons or []) if str(x).strip()]

    from core.agent_soul import append_lessons
    written = append_lessons(
        agent["id"], agent["name"], session.get("title") or "",
        lessons, taught_at=(session.get("updated_at") or "")[:16],
    )
    await update_training_session(
        session_id,
        status="done",
        lessons_json=json.dumps(lessons, ensure_ascii=False),
        result_notes="\n".join(f"- {x}" for x in lessons),
    )
    logger.info("Buổi dạy %s: ghi %d bài học vào soul nhân viên %s", session_id, written, agent["id"])
    return {"ok": True, "written": written, "agent_name": agent["name"]}


# ── SOUL.md ────────────────────────────────────────────────────────────────

@router.get("/soul")
async def get_soul():
    p = _soul_path()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"SOUL.md not found at: {p}")
    return {"content": p.read_text(encoding="utf-8")}


@router.post("/soul/append")
async def append_to_soul(req: AppendSoulRequest):
    p = _soul_path()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"SOUL.md not found at: {p}")

    try:
        current = p.read_text(encoding="utf-8")
        marker  = "## Ghi chú từ các session training"

        if marker in current:
            idx     = current.index(marker) + len(marker)
            updated = current[:idx] + "\n" + req.content.strip() + "\n" + current[idx:]
        else:
            updated = current.rstrip() + f"\n\n{marker}\n{req.content.strip()}\n"

        p.write_text(updated, encoding="utf-8")
        logger.info("SOUL.md updated at %s", p)
        return {"ok": True, "path": str(p)}
    except Exception as e:
        logger.exception("Failed to write SOUL.md at %s", p)
        raise HTTPException(status_code=500, detail=str(e))
