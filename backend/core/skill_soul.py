"""Phụ lục kỹ năng — bài học về NGHỀ mà Papa dạy, gắn vào một kỹ năng cụ thể.

Vì sao không ghi thẳng vào `skills.config_json.content`: phần content đó là bản
Papa viết tay trong tab Kỹ năng. Nếu bài học từ phòng dạy chèn thẳng vào đó thì
lần sau Papa mở tab Kỹ năng ra sửa sẽ không phân biệt được đâu là chữ mình viết,
đâu là chữ máy chèn — sửa một lần là mất bài học. Tách file riêng thì hai thứ
không giẫm chân nhau, và muốn xoá riêng phần Papa dạy vẫn xoá được.

Khác với soul dự án: phụ lục này CỐ Ý dùng chung cho mọi nhân viên và mọi dự án —
nó chỉ chứa điều đúng bất kể thương hiệu nào ("caption không dùng markdown"). Thứ
gì chỉ đúng với một thương hiệu thì thuộc về core/project_soul.py.
"""
from __future__ import annotations

import logging
from pathlib import Path

from core.soul_blocks import append_entry, block_inner

logger = logging.getLogger("xanax.skill_soul")

SKILL_SOULS_DIR = Path(__file__).parent.parent / "data" / "skill_souls"

_LESSON_START = "<!-- SKILL_LESSON_START -->"
_LESSON_END = "<!-- SKILL_LESSON_END -->"


def skill_soul_path(skill_id: int) -> Path:
    return SKILL_SOULS_DIR / f"skill_{skill_id}.md"


def read_skill_soul(skill_id: int) -> str:
    p = skill_soul_path(skill_id)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _seed_template(skill_name: str) -> str:
    return (
        f"# Phụ lục kỹ năng — {skill_name}\n\n"
        "## Bài học về nghề (Papa dạy trong phòng dạy AI)\n"
        f"{_LESSON_START}\n{_LESSON_END}\n"
    )


def ensure_skill_soul_file(skill_id: int, skill_name: str = "") -> Path:
    SKILL_SOULS_DIR.mkdir(parents=True, exist_ok=True)
    p = skill_soul_path(skill_id)
    if not p.exists():
        p.write_text(_seed_template(skill_name or f"#{skill_id}"), encoding="utf-8")
    return p


def has_skill_lessons(skill_id: int) -> bool:
    return bool(block_inner(read_skill_soul(skill_id), _LESSON_START, _LESSON_END))


def skill_soul_for_prompt(skill_id: int, skill_name: str = "") -> str:
    """Đoạn phụ lục để ghép ngay sau nội dung kỹ năng. Rỗng nếu chưa dạy gì."""
    inner = block_inner(read_skill_soul(skill_id), _LESSON_START, _LESSON_END)
    if not inner:
        return ""
    label = skill_name or f"kỹ năng #{skill_id}"
    return (
        f"### Papa đã dạy thêm về {label} (phần này ĐÈ LÊN mô tả kỹ năng phía trên "
        "nếu hai bên nói ngược nhau)\n" + inner
    )


def append_skill_lessons(skill_id: int, skill_name: str, session_title: str,
                         lessons: list[str], taught_at: str = "") -> int:
    lessons = [str(x).strip() for x in (lessons or []) if str(x).strip()]
    if not lessons:
        return 0

    ensure_skill_soul_file(skill_id, skill_name)
    header = f"\n**[Buổi dạy] {session_title or 'Không tên'}"
    header += f" — {taught_at}**" if taught_at else "**"
    entry = "\n".join([header] + [f"- {x}" for x in lessons])

    try:
        p = skill_soul_path(skill_id)
        p.write_text(append_entry(p.read_text(encoding="utf-8"), _LESSON_START, _LESSON_END, entry),
                     encoding="utf-8")
        logger.info("phụ lục kỹ năng %s: ghi %d bài học từ buổi dạy '%s'",
                    skill_id, len(lessons), session_title)
        return len(lessons)
    except Exception:
        logger.exception("append_skill_lessons lỗi ở kỹ năng %s", skill_id)
        return 0
