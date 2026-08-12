"""
Agent Soul — mỗi nhân viên AI (agent_configs) có 1 file soul.md riêng, mô phỏng lại
đúng cơ chế SOUL.md của Hermes/Xanax (xem core/soul_sync.py, api/websocket_training.py)
nhưng thu hẹp phạm vi về đúng 1 nhân viên thay vì cả công ty.

Mỗi file gồm 3 phần:
- Phần mô tả/tính cách (viết tay, giữ nguyên qua các lần sync — lấy từ system_prompt
  lúc tạo file, sau đó Papa có thể tự chỉnh sửa trực tiếp trong file).
- <!-- AGENT_DATA_START/END --> — snapshot tự động: vai trò, phòng ban, kỹ năng, công
  việc đang được giao — sync lại mỗi khi nhân viên chuẩn bị trả lời (họp/quy trình).
- <!-- AGENT_FEEDBACK_START/END --> — lịch sử phản hồi ĐẠT/KHÔNG ĐẠT từ Papa cho từng
  output của nhân viên này (xem api/routes/workflow.py) — nhân viên "tự cải thiện" bằng
  cách đọc lại các bài học này trước khi làm việc tiếp, giống hệt cách Hermes học từ
  SOUL.md chung, chỉ khác là mỗi nhân viên chỉ thấy bài học của riêng mình.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from core.soul_blocks import replace_block

logger = logging.getLogger("xanax.agent_soul")

SOULS_DIR = Path(__file__).parent.parent / "data" / "souls"

_DATA_START = "<!-- AGENT_DATA_START -->"
_DATA_END = "<!-- AGENT_DATA_END -->"
_FEEDBACK_START = "<!-- AGENT_FEEDBACK_START -->"
_FEEDBACK_END = "<!-- AGENT_FEEDBACK_END -->"
_MAX_FEEDBACK = 40  # giữ tối đa N mục gần nhất, xoá cũ nhất khi vượt

# Bài học Papa dạy trực tiếp trong phòng dạy AI (api/websocket_training.py).
# Cố tình TÁCH khỏi khối FEEDBACK dù hai bên đều là "bài học": FEEDBACK sinh ra
# từ việc chấm output có thật và bị cắt còn 40 mục gần nhất, nên nếu trộn chung
# thì thứ Papa đích thân dạy sẽ bị output thường ngày đẩy ra ngoài. Tách ra còn
# giữ được nguồn gốc — sau này muốn xoá riêng một loại vẫn làm được.
_LESSON_START = "<!-- AGENT_LESSON_START -->"
_LESSON_END = "<!-- AGENT_LESSON_END -->"


def soul_path(agent_id: int) -> Path:
    return SOULS_DIR / f"agent_{agent_id}.md"


def read_soul(agent_id: int) -> str:
    p = soul_path(agent_id)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _seed_template(agent: dict) -> str:
    persona = (agent.get("system_prompt") or "").strip() or (
        f"{agent.get('name', '?')} là {agent.get('role', 'Assistant')}, chưa có mô tả tính cách chi tiết."
    )
    return (
        f"# Soul — {agent.get('name', '?')}\n\n"
        "## Mô tả & Tính cách\n"
        f"{persona}\n\n"
        "## Dữ liệu thực tế (tự động đồng bộ)\n"
        f"{_DATA_START}\n{_DATA_END}\n\n"
        "## Bài học từ phản hồi thực tế (Papa chấm ĐẠT/KHÔNG ĐẠT)\n"
        f"{_FEEDBACK_START}\n{_FEEDBACK_END}\n\n"
        "## Bài học từ buổi dạy (Papa dạy trực tiếp)\n"
        f"{_LESSON_START}\n{_LESSON_END}\n"
    )


def ensure_soul_file(agent: dict) -> Path:
    """Tạo file soul.md cho nhân viên nếu chưa có — gọi ngay khi tạo agent_config mới."""
    SOULS_DIR.mkdir(parents=True, exist_ok=True)
    p = soul_path(agent["id"])
    if not p.exists():
        p.write_text(_seed_template(agent), encoding="utf-8")
        logger.info("Created soul.md for agent %s at %s", agent["id"], p)
    return p


# Dùng chung với soul dự án và phụ lục kỹ năng — xem core/soul_blocks.py.
_replace_block = replace_block


async def _build_agent_data_block(agent: dict) -> str:
    from hub.database import get_department, list_projects, list_work_items, get_skill, list_agent_run_history

    lines = [f"- Vai trò: {agent.get('role', '')}"]

    dept_id = agent.get("department_id")
    if dept_id:
        dept = await get_department(dept_id)
        if dept:
            is_head = dept.get("head_agent_id") == agent["id"]
            lines.append(f"- Phòng ban: {dept['name']}{' (trưởng phòng)' if is_head else ''}")
    else:
        lines.append("- Phòng ban: (chưa gán)")

    try:
        skill_ids = json.loads(agent.get("skills_json") or "[]")
    except Exception:
        skill_ids = []
    skill_names = []
    for sid in skill_ids:
        skill = await get_skill(sid)
        if skill:
            skill_names.append(skill["name"])
    lines.append(f"- Kỹ năng: {', '.join(skill_names) if skill_names else '(chưa có)'}")

    lines.append("- Công việc đang được giao:")
    found = False
    for p in await list_projects():
        for it in await list_work_items(p["id"]):
            if it.get("assigned_agent_id") == agent["id"]:
                lines.append(f"  - [{it['status']}] {it['title']} (dự án: {p['name']}, priority: {it.get('priority', '')})")
                found = True
    if not found:
        lines.append("  - (chưa có việc nào được giao)")

    lines.append("- Lịch sử chạy quy trình gần đây (không chỉ việc đang active):")
    runs = await list_agent_run_history(agent["id"], limit=10)
    if runs:
        for r in runs:
            verdict = f", đánh giá: {r['pass_fail']}" if r.get("pass_fail") else ""
            when = r.get("completed_at") or r.get("created_at") or ""
            lines.append(f"  - [{r.get('status', '')}] {r.get('task_name', '?')} lúc {when}{verdict}")
    else:
        lines.append("  - (chưa có lịch sử chạy quy trình nào)")

    return "\n".join(lines)


async def sync_agent_soul(agent: dict) -> None:
    """Đồng bộ lại phần dữ liệu thực tế trong soul.md — gọi trước mỗi lần nhân viên
    chuẩn bị trả lời (họp/quy trình), giống cơ chế soul_sync.py áp dụng cho Hermes."""
    try:
        p = ensure_soul_file(agent)
        text = p.read_text(encoding="utf-8")
        block = await _build_agent_data_block(agent)
        p.write_text(_replace_block(text, _DATA_START, _DATA_END, block), encoding="utf-8")
    except Exception:
        logger.exception("sync_agent_soul failed for agent %s", agent.get("id"))


def has_lessons(agent_id: int) -> bool:
    """Nhân viên này đã được Papa dạy buổi nào chưa."""
    text = read_soul(agent_id)
    if _LESSON_START not in text or _LESSON_END not in text:
        return False
    inner = text[text.index(_LESSON_START) + len(_LESSON_START):text.index(_LESSON_END)]
    return bool(inner.strip())


# Bài học Papa dạy và nội dung kỹ năng thường MÂU THUẪN nhau, và không có dòng
# này thì model theo kỹ năng.
#
# Ca thật: Papa dạy Celexa "khi câu đã đủ duyên thì dừng, không thêm vế thúc đẩy
# mua hàng ở cuối", trong khi kỹ năng write_post ghi cứng "CTA: câu kêu gọi hành
# động rõ ràng (comment / tag bạn / nhắn tin)". Bài đăng sinh ra kết thúc bằng
# đúng câu CTA đó. Kỹ năng là công thức từng bước rất dễ làm theo, còn bài học
# là nguyên tắc — model chọn cái cụ thể hơn.
#
# Thứ tự ghép prompt không đủ để giải quyết: soul đã nằm cuối cùng rồi mà vẫn
# thua. Phải nói thẳng cái nào thắng.
_LESSON_PRECEDENCE = (
    "THỨ TỰ ƯU TIÊN KHI CÓ MÂU THUẪN: phần 'Bài học từ buổi dạy' phía trên là do "
    "Papa đích thân dạy bạn, và nó ĐÈ LÊN mọi khuôn mẫu, cấu trúc hay công thức "
    "viết sẵn trong phần mô tả kỹ năng. Nếu kỹ năng bảo bạn luôn phải có một thành "
    "phần nào đó (ví dụ câu kêu gọi hành động ở cuối, một cấu trúc cố định, một số "
    "lượng hashtag) mà bài học của Papa nói ngược lại, hãy THEO BÀI HỌC CỦA PAPA và "
    "bỏ phần khuôn mẫu đó đi."
)


def soul_for_prompt(agent_id: int) -> str:
    """Soul để nhét vào system prompt, kèm dòng nêu thứ tự ưu tiên nếu có bài học.

    Dùng thay cho `read_soul` ở mọi nơi dựng prompt cho nhân viên (quy trình,
    phòng họp, phòng dạy). Chỉ gắn dòng ưu tiên khi thật sự có bài học — nhân
    viên chưa được dạy buổi nào mà đọc câu đó thì chỉ tổ nhiễu.
    """
    text = read_soul(agent_id)
    if not text or not has_lessons(agent_id):
        return text
    return f"{text}\n\n{_LESSON_PRECEDENCE}"


def append_lessons(agent_id: int, agent_name: str, session_title: str,
                   lessons: list[str], taught_at: str = "") -> int:
    """Ghi các bài học đã được Papa DUYỆT từ một buổi dạy vào soul của nhân viên.

    Trả về số mục thực sự ghi. Cố ý không cắt bớt theo số lượng như
    `append_feedback`: khối này chỉ lớn lên khi Papa đích thân dạy, và mất một
    bài đã dạy thì tệ hơn nhiều so với việc mất một dòng chấm output.

    Danh sách truyền vào phải là bản Papa đã xem và sửa (xem
    api/routes/training.py, POST /sessions/{id}/lessons). Hàm này KHÔNG tự
    chưng cất — nếu nó vừa tóm tắt vừa ghi thì không ai kiểm được thứ đi vào
    soul, mà soul thì ảnh hưởng mọi lần nhân viên làm việc sau đó.
    """
    lessons = [str(x).strip() for x in (lessons or []) if str(x).strip()]
    if not lessons:
        return 0

    p = soul_path(agent_id)
    if not p.exists():
        ensure_soul_file({"id": agent_id, "name": agent_name, "role": "", "system_prompt": ""})

    header = f"\n**[Buổi dạy] {session_title or 'Không tên'}"
    header += f" — {taught_at}**" if taught_at else "**"
    entry = "\n".join([header] + [f"- {x}" for x in lessons])

    try:
        text = p.read_text(encoding="utf-8")
        inner = ""
        if _LESSON_START in text and _LESSON_END in text:
            inner = text[text.index(_LESSON_START) + len(_LESSON_START):text.index(_LESSON_END)]
        new_inner = (inner.strip("\n") + "\n" + entry).strip("\n")
        p.write_text(_replace_block(text, _LESSON_START, _LESSON_END, new_inner), encoding="utf-8")
        logger.info("soul.md: ghi %d bài học từ buổi dạy '%s' cho nhân viên %s",
                    len(lessons), session_title, agent_id)
        return len(lessons)
    except Exception:
        logger.exception("append_lessons failed for agent %s", agent_id)
        return 0


def append_feedback(agent_id: int, agent_name: str, task_name: str, verdict: str, content: str, notes: str = "") -> None:
    """Ghi 1 mục ĐẠT/KHÔNG ĐẠT vào soul.md của đúng nhân viên đã tạo ra output đó —
    xem api/routes/workflow.py (PATCH /outputs/{id} với pass_fail)."""
    if verdict not in ("pass", "fail"):
        return
    p = soul_path(agent_id)
    if not p.exists():
        ensure_soul_file({"id": agent_id, "name": agent_name, "role": "", "system_prompt": ""})

    label = "ĐẠT" if verdict == "pass" else "KHÔNG ĐẠT"
    content = (content or "").strip()
    if len(content) > 800:
        content = content[:800] + "…"

    entry_lines = [f"\n**[{label}] {task_name}:**", content]
    if verdict == "fail" and notes:
        entry_lines.append(f"→ Ghi chú: {notes}")
    elif verdict == "pass":
        entry_lines.append("→ Output ĐẠT CHUẨN — giữ phong cách và chất lượng này ở lần sau")
    entry = "\n".join(entry_lines)

    try:
        text = p.read_text(encoding="utf-8")
        if _FEEDBACK_START in text and _FEEDBACK_END in text:
            inner_start = text.index(_FEEDBACK_START) + len(_FEEDBACK_START)
            inner_end = text.index(_FEEDBACK_END)
            inner = text[inner_start:inner_end]
            items = inner.split("\n**[")
            header, items = items[0], ["\n**[" + e for e in items[1:]]
            items.append(entry)
            if len(items) > _MAX_FEEDBACK:
                items = items[-_MAX_FEEDBACK:]
            new_inner = header + "".join(items)
            new_text = _replace_block(text, _FEEDBACK_START, _FEEDBACK_END, new_inner.strip("\n"))
        else:
            new_text = _replace_block(text, _FEEDBACK_START, _FEEDBACK_END, entry.strip("\n"))
        p.write_text(new_text, encoding="utf-8")
        logger.info("soul.md feedback updated for agent %s: [%s] %s", agent_id, label, task_name)
    except Exception:
        logger.exception("append_feedback failed for agent %s", agent_id)
