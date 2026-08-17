"""Khởi chạy MCP cắt ảnh bằng venv rembg riêng.

File này cố ý không import ``rembg``: nó chạy bằng venv chính của Xanax, tìm
Python của venv rembg rồi chuyển quyền thực thi sang ``image_cut.py``.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


REMBG_PYTHON_ENV = "XANAX_REMBG_PYTHON"
_LINUX_DEFAULT = Path("/opt/xanax/.venv-rembg/bin/python")
_WINDOWS_DEFAULT = Path(
    r"C:\Users\Quang\.claude\mcp-servers\rembg-mcp\.venv\Scripts\python.exe"
)
_SERVER_PATH = Path(__file__).with_name("image_cut.py")


def _default_python(os_name: str) -> Path | None:
    if os_name == "posix":
        return _LINUX_DEFAULT
    if os_name == "nt":
        return _WINDOWS_DEFAULT
    return None


def resolve_rembg_python(
    *, environ: dict[str, str] | None = None, os_name: str | None = None,
) -> Path:
    """Ưu tiên biến môi trường, sau đó mới dùng đường dẫn mặc định của hệ điều hành."""
    environ = os.environ if environ is None else environ
    os_name = os.name if os_name is None else os_name

    candidates: list[Path] = []
    configured = (environ.get(REMBG_PYTHON_ENV) or "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    default = _default_python(os_name)
    if default is not None and default not in candidates:
        candidates.append(default)

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    tried = ", ".join(str(path) for path in candidates) or "không có đường dẫn mặc định"
    raise FileNotFoundError(
        "Không tìm thấy Python của venv rembg. "
        f"Đã thử: {tried}. Hãy dựng venv rembg riêng theo deploy/README.md "
        f"hoặc đặt {REMBG_PYTHON_ENV} tới file python của venv đó."
    )


def launch(interpreter: Path, *, os_name: str | None = None) -> int:
    """Chạy server với stdio giữ nguyên; POSIX thay tiến trình, Windows chờ tiến trình con."""
    os_name = os.name if os_name is None else os_name
    argv = [str(interpreter), str(_SERVER_PATH)]
    if os_name == "nt":
        # Không dùng execv trên Windows: giữ launcher sống và cho tiến trình con
        # kế thừa nguyên stdin/stdout để phiên MCP không bị đứt giữa chừng.
        return subprocess.call(argv)

    os.execv(str(interpreter), argv)
    raise RuntimeError("os.execv trả về ngoài dự kiến")  # pragma: no cover


def main() -> int:
    try:
        interpreter = resolve_rembg_python()
        return launch(interpreter)
    except Exception as exc:
        # stdout dành riêng cho JSON-RPC của MCP; lỗi khởi động phải đi stderr.
        import sys

        print(f"Không khởi động được MCP cắt ảnh: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
