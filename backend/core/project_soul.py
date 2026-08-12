"""Soul dự án — giọng thương hiệu và luật riêng của TỪNG dự án.

Vì sao cần kho thứ ba, ngoài soul nhân viên và mô tả kỹ năng:

Trước đây chỉ có hai chỗ để nhét kiến thức — system_prompt của nhân viên và mô tả
kỹ năng. Nhưng thứ Papa dạy có ba loại khác nhau:

- "Celexa xưng em, gọi Sếp"           → thuộc về NGƯỜI  → soul nhân viên
- "caption không được dùng markdown"  → thuộc về NGHỀ   → mô tả kỹ năng
- "khách của shop len gọi là mấy bà"  → thuộc về THƯƠNG HIỆU → không có chỗ nào

Loại thứ ba trước đây bị nhét bừa vào một trong hai chỗ còn lại, và cả hai đều
sai: ghi vào kỹ năng thì nhân viên khác dùng chung kỹ năng đó cũng bị lây giọng
shop len; ghi vào nhân viên thì chính nhân viên đó sang dự án nội thất vẫn nói
giọng shop len. File này là chỗ đúng cho loại thứ ba.

Nhờ vậy cùng một nhân viên + cùng một kỹ năng, chạy trong dự án nào thì ra giọng
của dự án đó, không phải sửa gì cả.

Mỗi file gồm 3 phần:
- <!-- PROJECT_BRIEF_START/END --> — mô tả dự án, ĐỒNG BỘ TỰ ĐỘNG từ cột
  `projects.description` (tab Dự án). Sửa tay ở đây sẽ bị ghi đè — sửa trong tab.
- <!-- PROJECT_LESSON_START/END --> — bài học thương hiệu Papa duyệt từ phòng dạy
  (xem api/routes/training.py, POST /sessions/{id}/close).
- <!-- PROJECT_APPROVED_START/END --> — bài đã được duyệt ở cổng duyệt, máy tự ghi
  (xem _record_approval trong api/websocket_workflow.py).

Ngoài ba khối đó, Papa còn viết tay phần "Ví dụ bài đăng ĐẠT" nằm NGOÀI mọi khối.
Máy không bao giờ đụng vào phần đó — đấy là lý do khối APPROVED phải tách riêng
thay vì ghi chung: bài Papa tự tay chọn và bài máy gom về là hai mức tin cậy khác
nhau, trộn chung thì sau này không biết dòng nào do ai đặt vào.
"""
from __future__ import annotations

import logging
from pathlib import Path

from core.soul_blocks import append_entry, block_inner, replace_block

logger = logging.getLogger("xanax.project_soul")

PROJECT_SOULS_DIR = Path(__file__).parent.parent / "data" / "project_souls"

_BRIEF_START = "<!-- PROJECT_BRIEF_START -->"
_BRIEF_END = "<!-- PROJECT_BRIEF_END -->"
_LESSON_START = "<!-- PROJECT_LESSON_START -->"
_LESSON_END = "<!-- PROJECT_LESSON_END -->"
_APPROVED_START = "<!-- PROJECT_APPROVED_START -->"
_APPROVED_END = "<!-- PROJECT_APPROVED_END -->"

# Giữ tối đa mấy bài đã duyệt. Cố ý ít: mỗi bài dài 500–900 ký tự và đi vào prompt
# của MỌI lần chạy thuộc dự án này. Giữ 10 bài là soul dự án phình gấp ba, đẩy luật
# và bài mẫu viết tay xuống cuối một prompt dài — đúng thứ đã làm bài học thua khuôn
# mẫu kỹ năng trước đây. Ba bài đủ để model thấy vài lối viết khác nhau.
_MAX_APPROVED = 3


def project_soul_path(project_id: int) -> Path:
    return PROJECT_SOULS_DIR / f"project_{project_id}.md"


def read_project_soul(project_id: int) -> str:
    p = project_soul_path(project_id)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _seed_template(project: dict) -> str:
    return (
        f"# Soul dự án — {project.get('name', '?')}\n\n"
        "## Mô tả dự án (tự động đồng bộ từ tab Dự án — sửa ở đó, đừng sửa ở đây)\n"
        f"{_BRIEF_START}\n{_BRIEF_END}\n\n"
        "## Giọng thương hiệu & luật riêng của dự án (Papa dạy trong phòng dạy AI)\n"
        f"{_LESSON_START}\n{_LESSON_END}\n\n"
        "## Bài gần đây đã được duyệt (máy tự ghi khi Papa bấm Duyệt — viết theo lối này)\n"
        f"{_APPROVED_START}\n{_APPROVED_END}\n"
    )


def ensure_project_soul_file(project: dict) -> Path:
    PROJECT_SOULS_DIR.mkdir(parents=True, exist_ok=True)
    p = project_soul_path(project["id"])
    if not p.exists():
        p.write_text(_seed_template(project), encoding="utf-8")
        logger.info("Tạo soul dự án %s tại %s", project["id"], p)
    return p


def sync_project_brief(project: dict) -> None:
    """Chép mô tả dự án từ DB vào khối BRIEF. Gọi trước mỗi lần dựng prompt.

    Đồng bộ chứ không chỉ gieo một lần: Papa sửa mô tả trong tab Dự án thì lần
    chạy kế tiếp phải thấy mô tả mới, không phải bản chụp lúc tạo file.
    """
    try:
        p = ensure_project_soul_file(project)
        text = p.read_text(encoding="utf-8")
        brief = (project.get("description") or "").strip()
        if block_inner(text, _BRIEF_START, _BRIEF_END) == brief:
            return
        p.write_text(replace_block(text, _BRIEF_START, _BRIEF_END, brief), encoding="utf-8")
    except Exception:
        logger.exception("sync_project_brief lỗi ở dự án %s", project.get("id"))


def has_project_lessons(project_id: int) -> bool:
    return bool(block_inner(read_project_soul(project_id), _LESSON_START, _LESSON_END))


# Ba nguồn luật cùng nói về một bài đăng: mô tả kỹ năng, soul nhân viên, soul dự
# án. Không nói rõ cái nào thắng thì model theo cái CỤ THỂ nhất — thường là công
# thức từng bước trong mô tả kỹ năng — và giọng thương hiệu thua.
_PROJECT_PRECEDENCE = (
    "THỨ TỰ ƯU TIÊN KHI CÓ MÂU THUẪN: phần dự án phía trên là luật của dự án bạn "
    "đang làm. Khi bạn TẠO RA SẢN PHẨM (bài đăng, caption, email, kịch bản...), "
    "giọng và luật của dự án ĐÈ LÊN mọi khuôn mẫu viết sẵn trong mô tả kỹ năng, và "
    "đè lên cả thói quen chung của bản thân bạn. Kỹ năng chỉ dạy CÁCH LÀM, dự án "
    "quyết định NÓI VỚI AI VÀ NÓI GIỌNG GÌ."
)

# Chỉ nói câu này ở nơi THẬT SỰ có hội thoại (phòng họp, phòng dạy).
#
# Ca thật: câu này từng nằm chung với đoạn trên và đi vào cả prompt quy trình.
# Trong quy trình không có ai để nói chuyện, nhưng nó là dòng CUỐI CÙNG model đọc
# trước khi viết, nên có lần Celexa mở bài bằng "Sếp, em dùng skill imagegen vì..."
# và cả lời dẫn đó bị lưu thành nội dung bài đăng chờ duyệt.
_CONVERSATION_NOTE = (
    "Lưu ý: luật dự án ở trên chi phối SẢN PHẨM bạn tạo ra, không chi phối cách bạn "
    "nói chuyện. Khi trò chuyện với Papa, bạn vẫn giữ đúng tính cách riêng của mình."
)


def project_soul_for_prompt(project_id: int, mode: str = "product") -> str:
    """Đoạn soul dự án để nhét vào system prompt. Rỗng nếu dự án chưa có gì.

    mode="product"      — quy trình: nhân viên đang tạo ra sản phẩm giao đi.
    mode="conversation" — phòng họp / phòng dạy: nhân viên đang nói chuyện.

    Trả rỗng khi cả mô tả lẫn bài học đều trống: nhét vào một khung soul rỗng chỉ
    tổ nhiễu prompt, và câu nêu thứ tự ưu tiên khi chưa có luật nào để ưu tiên thì
    vô nghĩa.
    """
    text = read_project_soul(project_id)
    if not text:
        return ""
    brief = block_inner(text, _BRIEF_START, _BRIEF_END)
    lessons = block_inner(text, _LESSON_START, _LESSON_END)
    if not brief and not lessons:
        return ""
    out = f"{text.strip()}\n\n{_PROJECT_PRECEDENCE}"
    if mode == "conversation":
        out += f"\n\n{_CONVERSATION_NOTE}"
    return out


async def project_prompt(project_id: int | None, mode: str = "product") -> str:
    """Đồng bộ mô tả rồi trả đoạn soul dự án — dùng ở mọi chỗ dựng prompt."""
    if not project_id:
        return ""
    try:
        from hub.database import get_project
        project = await get_project(project_id)
        if not project:
            return ""
        sync_project_brief(project)
        return project_soul_for_prompt(project_id, mode)
    except Exception:
        logger.exception("project_prompt lỗi ở dự án %s", project_id)
        return ""


# Dấu mở đầu mỗi mục, dùng luôn làm chỗ cắt khi đếm lại số mục đang giữ. Cố ý
# KHÔNG kèm ký tự xuống dòng: `replace_block` strip hai đầu khối, nên mục đầu tiên
# không có newline đứng trước và phép cắt sẽ trượt mất nó.
_APPROVED_ITEM_SEP = "**[Đã duyệt]"


def append_approved_example(project_id: int, project_name: str, content: str,
                            original: str = "", approved_at: str = "") -> bool:
    """Ghi một bài Papa vừa bấm Duyệt vào soul dự án làm bài mẫu.

    Vì sao tự động: trước đây chỉ có lời CHÊ đi được vào soul (xem _record_rejection),
    còn bài đạt thì trôi qua không để lại gì. Nhân viên vì thế chỉ đọc được một danh
    sách những thứ không được làm, càng dạy càng viết dè dặt và nhạt đi. Bài đạt là
    thứ duy nhất dạy được PHẢI viết thế nào.

    `original` là bản máy sinh trước khi Papa sửa tay trong ô duyệt. Có nó thì ghi
    kèm cả cặp trước/sau: chỗ Papa đích thân sửa là tín hiệu sắc nhất trong cả hệ
    thống — nó chỉ thẳng ra khoảng cách giữa "máy viết được" và "Papa chịu đăng".

    Trả về True nếu có ghi. Chỉ giữ `_MAX_APPROVED` bài gần nhất.
    """
    content = (content or "").strip()
    if not project_id or not content:
        return False

    p = project_soul_path(project_id)
    if not p.exists():
        ensure_project_soul_file({"id": project_id, "name": project_name})

    header = f"{_APPROVED_ITEM_SEP} {approved_at}**" if approved_at else f"{_APPROVED_ITEM_SEP}**"

    lines = [header, "```", content, "```"]

    original = (original or "").strip()
    if original and original != content:
        lines += [
            "→ Papa đã SỬA TAY trước khi duyệt. Bản máy viết ra ban đầu:",
            "```", original, "```",
            "→ Đọc kỹ chỗ khác nhau giữa hai bản: đó là khoảng cách giữa bài viết được "
            "và bài đăng được.",
        ]
    entry = "\n".join(lines)

    try:
        text = p.read_text(encoding="utf-8")
        inner = block_inner(text, _APPROVED_START, _APPROVED_END)
        items = [_APPROVED_ITEM_SEP + x.rstrip("\n")
                 for x in inner.split(_APPROVED_ITEM_SEP)[1:]] if inner else []
        items.append(entry)
        new_inner = "\n\n".join(items[-_MAX_APPROVED:]).strip("\n")
        p.write_text(replace_block(text, _APPROVED_START, _APPROVED_END, new_inner), encoding="utf-8")
        logger.info("soul dự án %s: ghi 1 bài đã duyệt (giữ tối đa %d)", project_id, _MAX_APPROVED)
        return True
    except Exception:
        logger.exception("append_approved_example lỗi ở dự án %s", project_id)
        return False


def append_project_lessons(project_id: int, project_name: str, session_title: str,
                           lessons: list[str], taught_at: str = "") -> int:
    """Ghi bài học phạm vi DỰ ÁN mà Papa đã duyệt. Trả về số mục thực sự ghi.

    Giống `agent_soul.append_lessons`: không tự chưng cất, không cắt bớt theo số
    lượng. Danh sách truyền vào phải là bản Papa đã xem và sửa.
    """
    lessons = [str(x).strip() for x in (lessons or []) if str(x).strip()]
    if not lessons:
        return 0

    p = project_soul_path(project_id)
    if not p.exists():
        ensure_project_soul_file({"id": project_id, "name": project_name})

    header = f"\n**[Buổi dạy] {session_title or 'Không tên'}"
    header += f" — {taught_at}**" if taught_at else "**"
    entry = "\n".join([header] + [f"- {x}" for x in lessons])

    try:
        text = p.read_text(encoding="utf-8")
        p.write_text(append_entry(text, _LESSON_START, _LESSON_END, entry), encoding="utf-8")
        logger.info("soul dự án %s: ghi %d bài học từ buổi dạy '%s'",
                    project_id, len(lessons), session_title)
        return len(lessons)
    except Exception:
        logger.exception("append_project_lessons lỗi ở dự án %s", project_id)
        return 0
