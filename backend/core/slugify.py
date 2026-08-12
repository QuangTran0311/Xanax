"""Slugify tiếng Việt có dấu -> ascii kebab-case, dùng để đặt tên folder ổn định
cho dự án / quy trình (xem core/project_storage.py)."""
from __future__ import annotations

import re
import unicodedata

_NON_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, fallback: str = "untitled") -> str:
    text = (text or "").strip().lower().replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    text = _NON_SLUG_RE.sub("-", text).strip("-")
    return text or fallback
