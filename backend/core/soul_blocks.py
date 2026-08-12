"""Tiện ích đọc/ghi khối đánh dấu bằng HTML comment trong các file soul.

Tách ra vì giờ có ba kho soul dùng chung đúng một cơ chế: soul nhân viên
(core/agent_soul.py), soul dự án (core/project_soul.py) và phụ lục kỹ năng
(core/skill_soul.py). Ba file khác nhau, nhưng cùng một luật: phần Papa viết tay
nằm ngoài khối, phần máy ghi nằm trong khối, và ghi đè khối không được đụng tới
chữ bên ngoài.
"""
from __future__ import annotations


def replace_block(text: str, start: str, end: str, inner: str) -> str:
    """Thay nội dung giữa hai dấu mốc, giữ nguyên mọi thứ ngoài khối."""
    if start in text and end in text:
        before = text[: text.index(start)]
        after = text[text.index(end) + len(end):]
        return f"{before}{start}\n{inner}\n{end}{after}"
    # Khối bị xoá tay khỏi file — thêm lại ở cuối để không mất dữ liệu tiếp theo.
    return text.rstrip() + f"\n\n{start}\n{inner}\n{end}\n"


def block_inner(text: str, start: str, end: str) -> str:
    """Nội dung bên trong khối, đã strip. Chuỗi rỗng nếu không có khối."""
    if start not in text or end not in text:
        return ""
    return text[text.index(start) + len(start):text.index(end)].strip()


def append_entry(text: str, start: str, end: str, entry: str) -> str:
    """Thêm một mục vào cuối khối, giữ các mục cũ."""
    inner = block_inner(text, start, end)
    new_inner = (inner + "\n" + entry).strip("\n") if inner else entry.strip("\n")
    return replace_block(text, start, end, new_inner)
