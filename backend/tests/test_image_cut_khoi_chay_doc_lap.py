"""Kiểm tra đường khởi chạy image-cut thật, độc lập với sys.path của pytest."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _ghi_module(path: Path, noi_dung: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(noi_dung, encoding="utf-8")


def test_chay_image_cut_bang_duong_dan_tuyet_doi_tu_cwd_bat_ky(tmp_path):
    thu_muc_gia = tmp_path / "modules-gia"
    _ghi_module(thu_muc_gia / "rembg.py", """
def new_session(*args, **kwargs):
    return object()

def remove(*args, **kwargs):
    return b""
""")
    _ghi_module(thu_muc_gia / "onnxruntime.py", """
class SessionOptions:
    pass
""")
    _ghi_module(thu_muc_gia / "mcp" / "__init__.py", "")
    _ghi_module(thu_muc_gia / "mcp" / "server" / "__init__.py", "")
    _ghi_module(thu_muc_gia / "mcp" / "server" / "fastmcp.py", """
class FastMCP:
    def __init__(self, name):
        self.name = name

    def tool(self):
        return lambda function: function

    def run(self):
        return None
""")

    backend_dir = Path(__file__).resolve().parents[1]
    server_path = backend_dir / "mcp_servers" / "image_cut.py"
    cwd_bat_ky = tmp_path / "cwd-bat-ky"
    cwd_bat_ky.mkdir()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(thu_muc_gia)

    ket_qua = subprocess.run(
        [sys.executable, str(server_path)],
        cwd=cwd_bat_ky,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert ket_qua.returncode == 0, (
        f"stdout:\n{ket_qua.stdout}\nstderr:\n{ket_qua.stderr}"
    )
