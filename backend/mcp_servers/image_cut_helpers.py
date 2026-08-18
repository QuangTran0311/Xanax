"""Phần xử lý ảnh thuần, import được trên máy dev không cài rembg."""
from __future__ import annotations

import os
from collections.abc import Mapping

from PIL import Image

MAX_SIDE_ENV = "XANAX_IMAGE_CUT_MAX_SIDE"
IDLE_SECONDS_ENV = "XANAX_IMAGE_CUT_IDLE_SECONDS"


def read_nonnegative_env(
    name: str, default: int, environ: Mapping[str, str] | None = None,
) -> int:
    """Đọc số nguyên không âm; cấu hình hỏng quay về mặc định an toàn."""
    source = os.environ if environ is None else environ
    raw_value = source.get(name)
    if raw_value is None:
        return max(0, default)
    try:
        value = int(raw_value.strip())
    except (AttributeError, ValueError):
        return max(0, default)
    # Cả hai chốt RAM đều dùng 0 để tắt; số âm không có nghĩa hữu ích nên cũng
    # quy về 0 thay vì vô tình bật lại giá trị mặc định.
    return max(0, value)


def calculate_inference_size(
    original_size: tuple[int, int], max_side: int,
) -> tuple[int, int] | None:
    """Trả kích thước inference nhỏ hơn, hoặc None nếu không cần đụng ảnh."""
    width, height = original_size
    if max_side <= 0 or max(width, height) <= max_side:
        return None
    if width >= height:
        return (max_side, max(1, round(height * max_side / width)))
    return (max(1, round(width * max_side / height)), max_side)


def apply_alpha_to_original(original: Image.Image, alpha: Image.Image) -> Image.Image:
    """Phóng alpha về kích thước gốc rồi gắn lên đúng pixel ảnh gốc."""
    if alpha.mode != "L":
        alpha = alpha.getchannel("A")
    if alpha.size != original.size:
        alpha = alpha.resize(original.size, Image.Resampling.BILINEAR)
    result = original.convert("RGBA")
    result.putalpha(alpha)
    return result
