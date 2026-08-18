"""Phần xử lý ảnh thuần, import được trên máy dev không cài rembg."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from PIL import Image

MAX_SIDE_ENV = "XANAX_IMAGE_CUT_MAX_SIDE"
IDLE_SECONDS_ENV = "XANAX_IMAGE_CUT_IDLE_SECONDS"
SKIP_MEMORY_CHECK_ENV = "XANAX_IMAGE_CUT_SKIP_MEMORY_CHECK"

GIB = 1024 ** 3

# Số đo thật trên VPS production ngày 18/08/2026:
# - birefnet-general-lite: RSS đỉnh 5.562–5.628 MiB, 24–46 giây/ảnh. Ảnh test chỉ
#   485x711; ép đầu vào xuống 800px vẫn đạt đỉnh 5.562 MiB vì ONNX có input cố
#   định [1, 3, 1024, 1024], không có trục động. Đặt ngưỡng 6 GiB để có biên.
# - u2netp: RSS đỉnh 518 MiB, 0,7–2,3 giây/ảnh. Nhóm model nhẹ dùng ngưỡng 1 GiB.
# - Sau 30 giây nhàn rỗi RSS còn 127–138 MiB nhờ xóa session + malloc_trim.
# VPS lúc đo có MemTotal khoảng 5,8 GB và cgroup MemoryMax=5G, nên birefnet đang
# vượt trần. Không hạ ngưỡng theo kích thước ảnh đầu vào.
MODEL_MEMORY_REQUIREMENTS = {
    "birefnet-general-lite": 6 * GIB,
    "u2netp": 1 * GIB,
    "u2net": 1 * GIB,
    "isnet-general-use": 1 * GIB,
    "u2net_cloth_seg": 1 * GIB,
    "u2net_human_seg": 1 * GIB,
}
_LIGHT_MODEL_MEMORY = 1 * GIB


@dataclass(frozen=True)
class AvailableMemory:
    """RAM dùng được theo nguồn chặt nhất; ``bytes=None`` nghĩa là chưa biết."""

    bytes: int | None
    bottleneck: str | None


class InsufficientMemoryError(RuntimeError):
    """Chặn inference trước khi kernel phải chọn tiến trình để OOM-kill."""


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


def skip_memory_check(environ: Mapping[str, str] | None = None) -> bool:
    """Chỉ giá trị tường minh ``1`` mới tắt chốt RAM."""
    source = os.environ if environ is None else environ
    return source.get(SKIP_MEMORY_CHECK_ENV, "").strip() == "1"


def model_memory_requirement(model: str) -> tuple[int, bool]:
    """Trả ``(số byte yêu cầu, có chặn hay không)`` cho tên model.

    Mọi biến thể birefnet dùng ngưỡng nặng. Model lạ nhận ngưỡng nhóm nhẹ để
    báo/quan sát nhất quán nhưng không bị chặn vì chưa có số đo thực tế.
    """
    normalized = (model or "").strip().casefold()
    if normalized.startswith("birefnet"):
        return 6 * GIB, True
    if normalized in MODEL_MEMORY_REQUIREMENTS:
        return MODEL_MEMORY_REQUIREMENTS[normalized], True
    return _LIGHT_MODEL_MEMORY, False


def parse_mem_available(meminfo: str | None) -> int | None:
    """Đọc MemAvailable từ nội dung /proc/meminfo; lỗi coi như vô hạn."""
    if not meminfo:
        return None
    for line in meminfo.splitlines():
        key, separator, raw_value = line.partition(":")
        if not separator or key.strip() != "MemAvailable":
            continue
        parts = raw_value.split()
        if len(parts) < 2 or parts[1].casefold() != "kb":
            return None
        try:
            value_kib = int(parts[0])
        except ValueError:
            return None
        return value_kib * 1024 if value_kib >= 0 else None
    return None


def parse_cgroup_available(
    memory_max: str | None, memory_current: str | None,
) -> int | None:
    """Tính phần còn lại của cgroup v2; ``None`` nghĩa là không có giới hạn."""
    if memory_max is None or memory_current is None:
        return None
    max_value = memory_max.strip()
    if max_value == "max":
        return None
    try:
        limit = int(max_value)
        current = int(memory_current.strip())
    except (AttributeError, ValueError):
        return None
    if limit < 0 or current < 0:
        return None
    return max(0, limit - current)


def calculate_available_memory(
    meminfo: str | None,
    cgroup_memory_max: str | None,
    cgroup_memory_current: str | None,
) -> AvailableMemory:
    """Lấy giá trị nhỏ hơn giữa MemAvailable và phần còn lại của cgroup v2."""
    candidates = []
    mem_available = parse_mem_available(meminfo)
    if mem_available is not None:
        candidates.append((mem_available, "MemAvailable (/proc/meminfo)"))
    cgroup_available = parse_cgroup_available(
        cgroup_memory_max, cgroup_memory_current,
    )
    if cgroup_available is not None:
        candidates.append((
            cgroup_available,
            "trần cgroup (memory.max - memory.current)",
        ))
    if not candidates:
        return AvailableMemory(None, None)

    available = min(value for value, _ in candidates)
    bottlenecks = [source for value, source in candidates if value == available]
    return AvailableMemory(available, " và ".join(bottlenecks))


def _format_memory(byte_count: int) -> str:
    if byte_count < GIB:
        return f"{byte_count / (1024 ** 2):.0f} MiB"
    return f"{byte_count / GIB:.2f} GiB".replace(".00 GiB", " GiB")


def build_insufficient_memory_message(
    model: str,
    required_bytes: int,
    available_bytes: int,
    bottleneck: str,
) -> str:
    """Dựng thông báo đủ nghĩa để agent trả thẳng cho người vận hành."""
    return (
        f"Từ chối chạy model {model!r} để tránh OOM-kill: model cần ít nhất "
        f"{_format_memory(required_bytes)} RAM khả dụng nhưng hiện chỉ còn "
        f"{_format_memory(available_bytes)}; nút thắt là {bottleneck}. "
        "Hãy nâng RAM và đặt MemoryMax cao hơn đủ xa, hoặc dùng "
        "model='u2netp' (đo production 18/08/2026: RSS đỉnh 518 MiB, khoảng "
        "1–2 giây/ảnh; đánh đổi là có thể để sót bóng đổ). Khi chủ máy chấp "
        f"nhận rủi ro, có thể đặt {SKIP_MEMORY_CHECK_ENV}=1 để bỏ qua chốt này."
    )


def memory_check_error(
    model: str,
    meminfo: str | None,
    cgroup_memory_max: str | None,
    cgroup_memory_current: str | None,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Logic thuần quyết định có chặn inference hay không và trả lý do nếu chặn."""
    if skip_memory_check(environ):
        return None
    required, must_enforce = model_memory_requirement(model)
    if not must_enforce:
        return None
    available = calculate_available_memory(
        meminfo, cgroup_memory_max, cgroup_memory_current,
    )
    if available.bytes is None or available.bytes >= required:
        return None
    return build_insufficient_memory_message(
        model, required, available.bytes, available.bottleneck or "nguồn RAM khả dụng",
    )


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
