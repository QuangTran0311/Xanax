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
from fastapi.responses import FileResponse
from pydantic import BaseModel

from hub.database import (
    get_agent_config,
    get_project,
    get_skill,
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
    # Dự án của buổi dạy. Có nó thì học viên đọc được giọng thương hiệu của dự án
    # ngay trong lúc học, và bài học phạm vi "dự án" mới có chỗ để ghi vào.
    project_id: int | None = None


class UpdateSessionRequest(BaseModel):
    status: str | None = None          # 'in_progress' | 'pass' | 'fail'
    result_notes: str | None = None
    title: str | None = None
    task_description: str | None = None
    # Tên công cụ học viên được phép gọi trong buổi này. [] = không có công cụ nào.
    allowed_tools: list[str] | None = None


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
    if req.project_id is not None and not await get_project(req.project_id):
        raise HTTPException(status_code=400, detail="Không tìm thấy dự án được chọn")
    sid = await create_training_session(
        req.title, req.task_description, req.agent_id, req.project_id
    )
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
        allowed_tools_json=(json.dumps(req.allowed_tools)
                            if req.allowed_tools is not None else None),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return await get_training_session(session_id)


@router.get("/sessions/{session_id}/tools")
async def session_tools(session_id: int):
    """Công cụ có thể cấp cho học viên của buổi này, và cái nào đang được cấp.

    Danh sách ứng viên = đúng công cụ mà nhân viên đó vốn có (kỹ năng đã gắn, đã
    lọc theo phần công cụ được chọn trong nhóm MCP). Không bao giờ đề xuất thứ
    nhân viên không có — phòng dạy không phải chỗ cấp thêm quyền.
    """
    session = await get_training_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("agent_id"):
        return {"tools": [], "allowed": [], "note": "Buổi dạy này không có học viên."}

    agent = await get_agent_config(int(session["agent_id"]))
    if not agent:
        return {"tools": [], "allowed": [], "note": "Học viên đã bị xoá."}

    from api.websocket_meeting import _build_agent_tools
    schemas = await _build_agent_tools(agent)
    try:
        allowed = json.loads(session.get("allowed_tools_json") or "[]")
    except Exception:
        allowed = []
    return {
        "tools": [{"name": s["function"]["name"],
                   "description": s["function"].get("description", "")} for s in schemas],
        "allowed": allowed,
    }


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
    "Hãy rút ra những BÀI HỌC cần nhớ lâu dài, và XẾP MỖI BÀI VÀO ĐÚNG MỘT PHẠM VI.\n\n"
    "Ba phạm vi:\n"
    "- \"agent\" — thuộc về CON NGƯỜI {name}: cách xưng hô, tính cách, thói quen "
    "làm việc của riêng {name}. Chỉ đúng với {name}, người khác không áp dụng.\n"
    "- \"project\" — thuộc về THƯƠNG HIỆU của dự án: khách hàng là ai, gọi khách "
    "bằng gì, sản phẩm ra sao, được và không được nói gì về thương hiệu này. Đúng "
    "với BẤT KỲ nhân viên nào làm cho dự án này, và KHÔNG đúng khi sang dự án khác.\n"
    "- \"skill\" — thuộc về NGHỀ: đúng bất kể thương hiệu nào, người nào (ví dụ quy "
    "tắc định dạng, cách dựng câu mở đầu). Kèm thêm trường \"skill\" là TÊN kỹ năng.\n\n"
    "{scope_note}\n"
    "Quy tắc:\n"
    "- Chỉ lấy điều Papa THỰC SỰ đã dạy trong hội thoại. TUYỆT ĐỐI không suy diễn, "
    "không thêm bài học nghe hay nhưng Papa chưa hề nói.\n"
    "- Mỗi bài học là một câu ngắn, tự đứng một mình đọc vẫn hiểu (đừng viết kiểu "
    "\"như Papa nói ở trên\").\n"
    "- Viết ở dạng chỉ dẫn hành động: nên làm gì / tránh làm gì, chứ không kể lại "
    "diễn biến buổi học.\n"
    "- Phân vân giữa \"project\" và \"agent\" thì hỏi: người khác làm cho dự án này "
    "có cần biết điều này không? Có thì là \"project\".\n"
    "- Nếu buổi học chưa dạy được gì rõ ràng thì trả về mảng RỖNG. Trả mảng rỗng "
    "là câu trả lời hợp lệ và tốt hơn nhiều so với bịa ra bài học.\n\n"
    "Trả lời DUY NHẤT bằng JSON, không thêm chữ nào khác:\n"
    '{{"lessons": [{{"text": "...", "scope": "agent"}}, '
    '{{"text": "...", "scope": "skill", "skill": "tên kỹ năng"}}]}}'
)

_LESSONS_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

# Thẻ phạm vi hiển thị trong ô đúc kết. Papa sửa được bằng tay nên phải nhận cả
# bản có dấu lẫn không dấu — gõ nhanh thì hay rơi dấu.
SCOPE_LABELS = {"agent": "nhân viên", "project": "dự án", "skill": "kỹ năng"}
_SCOPE_ALIASES = {
    "agent": "agent", "nhân viên": "agent", "nhan vien": "agent", "nv": "agent",
    "project": "project", "dự án": "project", "du an": "project", "da": "project",
    "skill": "skill", "kỹ năng": "skill", "ky nang": "skill", "kn": "skill",
}


def _parse_lessons(raw: str) -> list[dict]:
    """Đọc JSON chưng cất → [{text, scope, skill}]. Bỏ qua mục không hợp lệ."""
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

    out: list[dict] = []
    for item in lessons:
        # Model cũ (hoặc model lười) trả mảng chuỗi — vẫn nhận, mặc định về phạm
        # vi nhân viên vì đó đúng bằng hành vi trước khi có phạm vi.
        if isinstance(item, str):
            text, scope, skill = item.strip(), "agent", ""
        elif isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            scope = _SCOPE_ALIASES.get(str(item.get("scope") or "").strip().lower(), "agent")
            skill = str(item.get("skill") or "").strip()
        else:
            continue
        if text:
            out.append({"text": text, "scope": scope, "skill": skill})
    return out


def _tag_lessons(lessons: list[dict]) -> str:
    """Dựng phần đúc kết dạng chữ có gắn thẻ, để Papa sửa thẳng trong textarea."""
    lines = []
    for x in lessons:
        tag = SCOPE_LABELS.get(x.get("scope") or "agent", "nhân viên")
        if x.get("scope") == "skill" and x.get("skill"):
            tag += f": {x['skill']}"
        lines.append(f"[{tag}] {x['text']}")
    return "\n".join(lines)


class CloseSessionRequest(BaseModel):
    # Phần đúc kết Papa đã sửa trong ô "Bài học ghi nhớ". Mỗi dòng là một bài
    # học; gửi chuỗi rỗng = đóng phòng mà không ghi gì vào soul.
    notes: str = ""


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
        return {"lessons": [], "notes": "", "note": "Buổi học chưa có nội dung nào."}

    transcript = "\n".join(
        f"{'Papa' if m['role'] == 'user' else agent['name']}: {m['content']}"
        for m in messages
    )
    system = _DISTILL_PROMPT.format(
        name=agent["name"],
        role=agent.get("role") or "nhân viên AI",
        scope_note=await _scope_note(session, agent),
    )

    from core.hermes_bridge import hermes
    raw = await hermes.complete_with_context([
        {"role": "system", "content": system},
        {"role": "user", "content": transcript},
    ])
    lessons = _normalise_scopes(_parse_lessons(raw), session, await _agent_skills(agent))

    await update_training_session(session_id, lessons_json=json.dumps(lessons, ensure_ascii=False))
    return {
        "lessons": lessons,
        "notes": _tag_lessons(lessons),
        "agent_name": agent["name"],
        "agent_id": agent["id"],
    }


async def _agent_skills(agent: dict) -> list[dict]:
    try:
        skill_ids = json.loads(agent.get("skills_json") or "[]")
    except Exception:
        return []
    out = []
    for sid in skill_ids:
        skill = await get_skill(sid)
        if skill:
            out.append({"id": skill["id"], "name": skill["name"]})
    return out


async def _scope_note(session: dict, agent: dict) -> str:
    """Nói thẳng cho model biết phạm vi nào dùng được trong buổi này.

    Không có đoạn này thì model xếp bài học vào "project" cho một buổi dạy không
    gắn dự án, và bài học đó không có chỗ nào để ghi.
    """
    lines = []
    if session.get("project_name"):
        lines.append(f'Buổi dạy này thuộc dự án "{session["project_name"]}" — '
                     'phạm vi "project" ghi vào dự án đó.')
    else:
        lines.append('Buổi dạy này KHÔNG gắn dự án nào — TUYỆT ĐỐI không dùng phạm '
                     'vi "project", hãy xếp vào "agent" hoặc "skill".')
    skills = await _agent_skills(agent)
    if skills:
        lines.append("Kỹ năng " + agent["name"] + " đang có: "
                     + ", ".join(s["name"] for s in skills) + ".")
    else:
        lines.append(f'{agent["name"]} chưa được gắn kỹ năng nào — không dùng phạm vi "skill".')
    return "\n".join(lines) + "\n"


def _normalise_scopes(lessons: list[dict], session: dict, skills: list[dict]) -> list[dict]:
    """Hạ phạm vi không dùng được về "agent" thay vì đánh rơi bài học.

    Model vẫn gán "project" cho buổi không có dự án dù prompt đã cấm. Bỏ bài học
    đó đi thì Papa mất công dạy; ghi vào nhân viên thì vẫn còn, chỉ hẹp hơn.
    """
    by_name = {s["name"].strip().lower(): s for s in skills}
    for x in lessons:
        if x["scope"] == "project" and not session.get("project_id"):
            x["scope"] = "agent"
        elif x["scope"] == "skill":
            hit = by_name.get(x.get("skill", "").strip().lower())
            if hit is None and len(skills) == 1:
                hit = skills[0]     # chỉ có một kỹ năng thì không có gì để nhầm
            if hit is None:
                x["scope"] = "agent"
            else:
                x["skill"] = hit["name"]
                x["skill_id"] = hit["id"]
    return lessons


_TAG_RE = re.compile(r"^\[([^\]]{1,60})\]\s*(.*)$")


def _lessons_from_notes(notes: str) -> list[dict]:
    """Tách phần đúc kết Papa đã sửa thành từng bài học, mỗi dòng một bài.

    Bỏ dấu đầu dòng ("- ", "• ", "1. ") vì `append_lessons` tự thêm lại; không
    bỏ thì soul ra "- - Bài học".

    Dòng mở đầu bằng "[dự án] " / "[kỹ năng: write_post] " thì đó là phạm vi Papa
    chọn. Không có thẻ, hoặc thẻ lạ, thì về "agent" — đúng bằng hành vi cũ, và
    hiểu nhầm một bài học thành của riêng nhân viên vẫn đỡ hơn là ghi nhầm giọng
    thương hiệu vào kỹ năng dùng chung.
    """
    out: list[dict] = []
    for line in (notes or "").splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if not line:
            continue
        scope, skill = "agent", ""
        m = _TAG_RE.match(line)
        if m:
            tag, rest = m.group(1).strip(), m.group(2).strip()
            head, _, tail = tag.partition(":")
            resolved = _SCOPE_ALIASES.get(head.strip().lower())
            if resolved and rest:
                scope, skill, line = resolved, tail.strip(), rest
        out.append({"text": line, "scope": scope, "skill": skill})
    return out


@router.get("/sessions/{session_id}/image/{name}")
async def training_image(session_id: int, name: str):
    """Ảnh học viên vẽ thử ngay trong buổi học (xem _maybe_draw_in_class).

    Chỉ trả file nằm trong đúng thư mục của buổi học đó — `name` đến từ URL nên
    phải chặn ../ leo ra ngoài, giống cách archive-file của quy trình làm.
    """
    from api.websocket_training import TRAINING_IMAGE_DIR

    base = (TRAINING_IMAGE_DIR / str(session_id)).resolve()
    target = (base / name).resolve()
    if base not in target.parents or not target.is_file():
        raise HTTPException(404, "Không tìm thấy ảnh")
    return FileResponse(target)


@router.post("/sessions/{session_id}/close")
async def close_session(session_id: int, req: CloseSessionRequest):
    """Đóng buổi dạy — và CHỈ ở đây phòng mới đóng.

    Bấm Đạt / Cần cải thiện trước đó chỉ ghi kết quả đánh giá và dựng bản nháp
    đúc kết; phòng vẫn mở để Papa sửa phần đúc kết. Gộp hai việc lại (như bản
    cũ) khiến bấm Đạt là phòng đóng ngay, bản nháp do model viết đi thẳng vào
    soul mà Papa chưa kịp đọc.
    """
    session = await get_training_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    notes = (req.notes or "").strip()
    lessons = _lessons_from_notes(notes)
    written = {"agent": 0, "project": 0, "skill": 0}
    agent_name = None

    if session.get("agent_id"):
        agent = await get_agent_config(int(session["agent_id"]))
        if not agent:
            raise HTTPException(status_code=400,
                                detail="Học viên đã bị xoá khỏi danh sách nhân viên")
        agent_name = agent["name"]
        lessons = _normalise_scopes(lessons, session, await _agent_skills(agent))
        title = session.get("title") or ""
        taught_at = (session.get("updated_at") or "")[:16]

        def texts(scope: str, skill_id: int | None = None) -> list[str]:
            return [x["text"] for x in lessons
                    if x["scope"] == scope
                    and (skill_id is None or x.get("skill_id") == skill_id)]

        from core.agent_soul import append_lessons
        written["agent"] = append_lessons(
            agent["id"], agent["name"], title, texts("agent"), taught_at=taught_at)

        if session.get("project_id"):
            from core.project_soul import append_project_lessons
            written["project"] = append_project_lessons(
                int(session["project_id"]), session.get("project_name") or "",
                title, texts("project"), taught_at=taught_at)

        from core.skill_soul import append_skill_lessons
        for sid in {x["skill_id"] for x in lessons
                    if x["scope"] == "skill" and x.get("skill_id")}:
            name = next(x.get("skill", "") for x in lessons if x.get("skill_id") == sid)
            written["skill"] += append_skill_lessons(
                sid, name, title, texts("skill", sid), taught_at=taught_at)

    await update_training_session(
        session_id,
        result_notes=notes,
        lessons_json=json.dumps(lessons, ensure_ascii=False),
        closed=True,
    )
    logger.info("Đóng buổi dạy %s: ghi %d bài học nhân viên, %d dự án, %d kỹ năng (%s)",
                session_id, written["agent"], written["project"], written["skill"],
                agent_name or "dạy Xanax")
    return {
        "ok": True,
        "written": sum(written.values()),
        "written_by_scope": written,
        "agent_name": agent_name,
        "project_name": session.get("project_name"),
    }


@router.post("/sessions/{session_id}/reopen")
async def reopen_session(session_id: int):
    """Mở lại buổi dạy đã đóng để dạy tiếp / sửa lại đúc kết."""
    if not await get_training_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    await update_training_session(session_id, closed=False)
    return await get_training_session(session_id)


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
