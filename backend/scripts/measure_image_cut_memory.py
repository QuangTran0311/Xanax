r"""Đo RSS của skill cắt ảnh ngay trong venv rembg trên VPS.

Lệnh mẫu:
    sudo -u xanax /opt/xanax/.venv-rembg/bin/python \
      /opt/xanax/backend/scripts/measure_image_cut_memory.py <ảnh>

Đo gần baseline (không thu nhỏ ảnh, không xóa session khi idle):
    sudo -u xanax env XANAX_IMAGE_CUT_MAX_SIDE=0 XANAX_IMAGE_CUT_IDLE_SECONDS=0 \
      /opt/xanax/.venv-rembg/bin/python \
      /opt/xanax/backend/scripts/measure_image_cut_memory.py <ảnh>
"""
from __future__ import annotations

import argparse
import os
import resource
import sys
import tempfile
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# FastMCP dò .env theo cwd; chạy từ /root bằng sudo -u xanax sẽ PermissionError.
# Phải chdir như bẫy tương tự đã xử lý trong image_cut_launcher.py.
os.chdir(_BACKEND_DIR)
try:
    from mcp_servers.image_cut import _cut_one
except Exception as exc:
    print(
        "Không thể import bộ cắt ảnh. Hãy chạy script bằng Python của venv rembg "
        f"và kiểm tra XANAX_REMBG_PYTHON: {exc}",
        file=sys.stderr,
    )
    raise SystemExit(1) from None


def _current_rss_kib() -> int:
    """Đọc RSS hiện tại từ procfs; script này chủ đích chỉ chạy trên Linux VPS."""
    with Path("/proc/self/status").open(encoding="utf-8") as status:
        for line in status:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    raise RuntimeError("Không tìm thấy VmRSS trong /proc/self/status")


def _peak_rss_kib() -> int:
    """Linux báo ru_maxrss theo KiB, đủ để bắt đỉnh xảy ra bên trong inference."""
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _mib(value_kib: int) -> float:
    return value_kib / 1024


def main() -> int:
    parser = argparse.ArgumentParser(description="Đo RSS trước/sau bản vá cắt ảnh")
    parser.add_argument("image", type=Path)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--rest-seconds", type=float, default=30.0)
    parser.add_argument("--model", default="birefnet-general-lite")
    args = parser.parse_args()

    if not args.image.is_file():
        parser.error(f"Không tìm thấy ảnh: {args.image}")
    if args.runs <= 0:
        parser.error("--runs phải lớn hơn 0")
    if args.rest_seconds < 0:
        parser.error("--rest-seconds không được âm")

    print(f"RSS ban đầu: {_mib(_current_rss_kib()):.1f} MiB")
    with tempfile.TemporaryDirectory(prefix="xanax-image-cut-memory-") as temp_dir:
        output_path = Path(temp_dir) / "ket-qua.png"
        for index in range(1, args.runs + 1):
            started = time.monotonic()
            _cut_one(
                str(args.image), str(output_path), args.model, 2.0, "",
                "transparent", False,
            )
            print(
                f"Lần {index}/{args.runs}: RSS hiện tại "
                f"{_mib(_current_rss_kib()):.1f} MiB, đỉnh "
                f"{_mib(_peak_rss_kib()):.1f} MiB, "
                f"{time.monotonic() - started:.1f}s",
            )

        print(f"Nghỉ {args.rest_seconds:g}s để allocator/session có thời gian dọn...")
        time.sleep(args.rest_seconds)

    print(f"RSS đỉnh: {_mib(_peak_rss_kib()):.1f} MiB")
    print(f"RSS sau khi nghỉ: {_mib(_current_rss_kib()):.1f} MiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
