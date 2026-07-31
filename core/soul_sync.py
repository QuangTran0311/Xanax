"""
Soul Sync — tự động cập nhật dữ liệu công ty vào SOUL.md của Hermes mỗi khi Xanax khởi động.
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger("xanax.soul_sync")

_MARKER_START = "<!-- XANAX_DATA_START -->"
_MARKER_END   = "<!-- XANAX_DATA_END -->"


def _soul_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "SOUL.md"


async def sync_soul_md() -> None:
    """Đọc DB và ghi dữ liệu mới nhất vào block dữ liệu trong SOUL.md."""
    soul_path = _soul_path()
    if not soul_path.exists():
        logger.warning("SOUL.md not found at %s — skipping sync", soul_path)
        return

    try:
        block = await _build_data_block()
        _write_block(soul_path, block)
        logger.info("SOUL.md synced with latest Xanax data")
    except Exception:
        logger.exception("soul_sync failed — SOUL.md not updated")


async def _build_data_block() -> str:
    import json
    from hub.database import (
        list_agent_configs, list_skills, list_projects,
        list_work_items, list_workflow_tasks,
    )

    lines = ["**Dữ liệu công ty Xanax — tự động sync khi có thay đổi:**\n"]

    # Nhân viên
    lines.append("Nhân viên (enabled):")
    agents = await list_agent_configs()
    skills_all = await list_skills()
    skill_map = {s["id"]: s["name"] for s in skills_all}
    enabled_agents = [a for a in agents if a.get("enabled", 1)]
    if enabled_agents:
        for a in enabled_agents:
            try:
                skill_ids = json.loads(a.get("skills_json") or "[]")
                skill_names = [skill_map.get(i, str(i)) for i in skill_ids]
            except Exception:
                skill_names = []
            skills_str = ", ".join(skill_names) if skill_names else "không có"
            lines.append(f"- {a['name']} | {a['role']} | model: {a['model']} | skills: [{skills_str}]")
    else:
        lines.append("- (chưa có nhân viên)")

    # Kỹ năng
    lines.append("\nKỹ năng:")
    enabled_skills = [s for s in skills_all if s.get("enabled", 1)]
    if enabled_skills:
        for s in enabled_skills:
            lines.append(f"- {s['name']} — {s.get('description', '')}")
    else:
        lines.append("- (chưa có kỹ năng)")

    # Dự án
    lines.append("\nDự án:")
    projects = await list_projects()
    if projects:
        for p in projects:
            desc = (p.get("description") or "")[:80]
            lines.append(f"- [{p['status']}] {p['name']} — {desc}")
    else:
        lines.append("- (chưa có dự án)")

    # Công việc
    lines.append("\nCông việc:")
    project_map = {p["id"]: p["name"] for p in projects}
    all_items = []
    for p in projects:
        items = await list_work_items(p["id"])
        all_items.extend(items)
    if all_items:
        for i in all_items:
            pname = project_map.get(i.get("project_id"), "?")
            lines.append(f"- [{i['status']}] {i['title']} (dự án: {pname}, priority: {i.get('priority', '')})")
    else:
        lines.append("- (chưa có công việc)")

    # Quy trình
    lines.append("\nQuy trình:")
    workflows = await list_workflow_tasks()
    if workflows:
        for w in workflows:
            pname = project_map.get(w.get("project_id"), "?")
            lines.append(f"- {w['name']} — {w.get('description', '')} (dự án: {pname})")
    else:
        lines.append("- (chưa có quy trình)")

    # Lần chạy quy trình gần đây
    from hub.database import list_workflow_runs, list_finalized_meetings
    lines.append("\nLần chạy quy trình gần đây:")
    recent_runs = await list_workflow_runs(limit=5)
    if recent_runs:
        for r in recent_runs:
            when = r.get("completed_at") or r.get("started_at") or r.get("created_at")
            lines.append(f"- [{r['status']}] {r['task_name']} — trigger: {r.get('triggered_by','')} lúc {when}")
    else:
        lines.append("- (chưa có lần chạy nào)")

    # Quyết định đã chốt gần đây (chỉ những gì đã chốt mới được Xanax dùng để tự hành động)
    lines.append("\nQuyết định đã chốt gần đây (meeting đã finalize):")
    finalized = await list_finalized_meetings(limit=5)
    if finalized:
        for m in finalized:
            pname = project_map.get(m.get("project_id"), "?") if m.get("project_id") else "—"
            lines.append(f"- [{m.get('decided_at','')}] {m['title']} (dự án: {pname}): {m.get('decision_text','')}")
    else:
        lines.append("- (chưa có quyết định nào được chốt)")

    lines.append(
        "\nVai trò của Xanax: giám sát kiêm quản lý dự án cho Papa (CEO). Papa hỏi gì về nhân viên/dự "
        "án/quy trình/lần chạy/quyết định → chỉ dùng dữ liệu trên để báo cáo, không tự thêm/suy đoán. "
        "Xanax chỉ được tự động kích hoạt quy trình khi có quyết định đã chốt (mục trên) hoặc khi Papa "
        "ra lệnh trực tiếp — không tự ý ra lệnh khi kế hoạch chưa được chốt."
    )
    return "\n".join(lines)


_FEEDBACK_START = "<!-- XANAX_FEEDBACK_START -->"
_FEEDBACK_END   = "<!-- XANAX_FEEDBACK_END -->"
_MAX_FEEDBACK   = 40  # giữ tối đa N mục, xóa cũ nhất khi vượt


def append_feedback_to_soul(output: dict) -> None:
    """Ghi pass/fail output vào block phản hồi trong SOUL.md để Xanax học."""
    soul_path = _soul_path()
    if not soul_path.exists():
        logger.warning("SOUL.md not found — skipping feedback write")
        return

    verdict = output.get("pass_fail", "")
    if verdict not in ("pass", "fail"):
        return

    label = "ĐẠT" if verdict == "pass" else "KHÔNG ĐẠT"
    agent = output.get("agent_name", "?")
    task = output.get("task_name", "?")
    content = (output.get("edited_content") or output.get("output_content") or "").strip()
    notes = (output.get("notes") or "").strip()

    # Giới hạn độ dài content để không làm SOUL.md quá lớn
    if len(content) > 800:
        content = content[:800] + "…"

    entry_lines = [
        f"\n**[{label}] {agent} — {task}:**",
        content,
    ]
    if verdict == "fail" and notes:
        entry_lines.append(f"→ Ghi chú: {notes}")
    elif verdict == "pass":
        entry_lines.append("→ Đây là output ĐẠT CHUẨN — học phong cách và chất lượng này")
    entry = "\n".join(entry_lines)

    try:
        text = soul_path.read_text(encoding="utf-8")

        if _FEEDBACK_START in text and _FEEDBACK_END in text:
            before = text[:text.index(_FEEDBACK_START)]
            inner_start = text.index(_FEEDBACK_START) + len(_FEEDBACK_START)
            inner_end = text.index(_FEEDBACK_END)
            inner = text[inner_start:inner_end]
            after = text[inner_end + len(_FEEDBACK_END):]

            # Đếm số mục, xóa cũ nếu quá giới hạn
            entries = inner.split("\n**[")
            header = entries[0]
            items = ["\n**[" + e for e in entries[1:]]
            items.append(entry)
            if len(items) > _MAX_FEEDBACK:
                items = items[-_MAX_FEEDBACK:]
            new_inner = header + "".join(items)
        else:
            header = "\n## Phản hồi chất lượng từ Papa (workflow pass/fail):\n"
            new_inner = header + entry
            before = text.rstrip() + "\n\n"
            after = "\n"

        new_text = before + _FEEDBACK_START + new_inner + "\n" + _FEEDBACK_END + after
        soul_path.write_text(new_text, encoding="utf-8")
        logger.info("SOUL.md feedback updated: [%s] %s — %s", label, agent, task)

    except Exception:
        logger.exception("append_feedback_to_soul failed")


def _write_block(soul_path: Path, block: str) -> None:
    content = soul_path.read_text(encoding="utf-8")
    new_section = f"{_MARKER_START}\n{block}\n{_MARKER_END}"

    if _MARKER_START in content and _MARKER_END in content:
        before = content[:content.index(_MARKER_START)]
        after  = content[content.index(_MARKER_END) + len(_MARKER_END):]
        content = before + new_section + after
    else:
        content = content.rstrip() + "\n\n" + new_section + "\n"

    soul_path.write_text(content, encoding="utf-8")
