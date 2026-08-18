"""Launcher cắt ảnh phải kiểm tra được mà không cài rembg trên máy dev."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from core.mcp_client import (
    IMAGE_CUT_MCP_TARGET, _stdio_subprocess_env, resolve_builtin_stdio_target,
)
from mcp_servers import image_cut_launcher as launcher


def test_uu_tien_python_tu_bien_moi_truong(tmp_path):
    configured = tmp_path / "python-rembg"
    configured.touch()

    assert launcher.resolve_rembg_python(
        environ={launcher.REMBG_PYTHON_ENV: str(configured)}, os_name="posix",
    ) == Path(os.path.abspath(configured))


def test_giu_symlink_cua_python_venv(tmp_path):
    python_thuc = tmp_path / "python-thuc"
    python_thuc.touch()
    python_venv = tmp_path / "python-venv"
    try:
        python_venv.symlink_to(python_thuc)
    except OSError as exc:
        pytest.skip(f"Môi trường không cho phép tạo symlink: {exc}")

    resolved = launcher.resolve_rembg_python(
        environ={launcher.REMBG_PYTHON_ENV: str(python_venv)}, os_name="posix",
    )

    assert resolved == Path(os.path.abspath(python_venv))
    assert resolved != Path(os.path.abspath(python_thuc))


def test_chuan_hoa_dot_dot_ma_khong_resolve(tmp_path):
    thu_muc = tmp_path / "venv" / "bin"
    thu_muc.mkdir(parents=True)
    python_venv = tmp_path / "venv" / "python"
    python_venv.touch()
    configured = thu_muc / ".." / "python"

    assert launcher.resolve_rembg_python(
        environ={launcher.REMBG_PYTHON_ENV: str(configured)}, os_name="posix",
    ) == python_venv


def test_fallback_theo_he_dieu_hanh(monkeypatch, tmp_path):
    linux_python = tmp_path / ".venv-rembg" / "bin" / "python"
    linux_python.parent.mkdir(parents=True)
    linux_python.touch()
    monkeypatch.setattr(launcher, "_LINUX_DEFAULT", linux_python)

    assert launcher.resolve_rembg_python(
        environ={}, os_name="posix",
    ) == Path(os.path.abspath(linux_python))


def test_bao_loi_co_huong_dan_khi_khong_tim_thay(tmp_path):
    missing = tmp_path / "khong-co-python"
    with pytest.raises(FileNotFoundError) as exc_info:
        launcher.resolve_rembg_python(
            environ={launcher.REMBG_PYTHON_ENV: str(missing)}, os_name="unknown",
        )

    message = str(exc_info.value)
    assert launcher.REMBG_PYTHON_ENV in message
    assert "deploy/README.md" in message


def test_posix_exec_dung_python_va_image_cut(monkeypatch):
    calls = []

    def fake_execv(command, argv):
        calls.append((command, argv))
        raise RuntimeError("đã chặn exec trong test")

    monkeypatch.setattr(launcher.os, "chdir", lambda path: None)
    monkeypatch.setattr(launcher.os, "execv", fake_execv)
    with pytest.raises(RuntimeError, match="đã chặn"):
        launcher.launch(Path(sys.executable), os_name="posix")

    command, argv = calls[0]
    assert command == sys.executable
    assert argv == [sys.executable, str(launcher._SERVER_PATH)]


def test_posix_dat_cwd_backend_truoc_khi_exec(monkeypatch):
    events = []

    monkeypatch.setattr(launcher.os, "chdir", lambda path: events.append(("chdir", path)))

    def fake_execv(command, argv):
        events.append(("execv", command, argv))
        raise RuntimeError("đã chặn exec trong test")

    monkeypatch.setattr(launcher.os, "execv", fake_execv)
    with pytest.raises(RuntimeError, match="đã chặn"):
        launcher.launch(Path(sys.executable), os_name="posix")

    assert events[0] == ("chdir", launcher._BACKEND_DIR)
    assert events[1][0] == "execv"


def test_main_nhan_python_bat_ky_tu_bien_moi_truong(monkeypatch):
    calls = []
    monkeypatch.setenv(launcher.REMBG_PYTHON_ENV, sys.executable)
    monkeypatch.setattr(launcher, "launch", lambda interpreter: calls.append(interpreter) or 0)

    assert launcher.main() == 0
    assert calls == [Path(os.path.abspath(sys.executable))]


def test_windows_khong_dung_execv_va_giu_stdio_cho_tien_trinh_con(monkeypatch):
    calls = []
    monkeypatch.setattr(
        launcher.subprocess, "call",
        lambda argv, **kwargs: calls.append((argv, kwargs)) or 7,
    )

    assert launcher.launch(Path(sys.executable), os_name="nt") == 7
    assert calls == [(
        [sys.executable, str(launcher._SERVER_PATH)],
        {"cwd": launcher._BACKEND_DIR},
    )]


def test_target_noi_bo_doi_thanh_python_venv_chinh_va_launcher_tuyet_doi():
    command, args = resolve_builtin_stdio_target(IMAGE_CUT_MCP_TARGET)

    assert command == sys.executable
    assert len(args) == 1
    assert Path(args[0]).is_absolute()
    assert Path(args[0]).name == "image_cut_launcher.py"
    assert resolve_builtin_stdio_target("python server.py") is None


def test_env_stdio_giu_home_va_cho_config_ghi_de(monkeypatch):
    monkeypatch.setenv("HOME", "/home/xanax")
    monkeypatch.setenv("XANAX_REMBG_PYTHON", "/opt/rembg/python")
    monkeypatch.setenv("XANAX_IMAGE_CUT_MAX_SIDE", "1800")
    monkeypatch.setenv("XANAX_IMAGE_CUT_IDLE_SECONDS", "300")
    monkeypatch.setenv("XANAX_IMAGE_CUT_SKIP_MEMORY_CHECK", "1")

    env = _stdio_subprocess_env({"HOME": "/srv/custom-home", "RIENG": "1"})

    assert env["HOME"] == "/srv/custom-home"
    assert env["XANAX_REMBG_PYTHON"] == "/opt/rembg/python"
    assert env["XANAX_IMAGE_CUT_MAX_SIDE"] == "1800"
    assert env["XANAX_IMAGE_CUT_IDLE_SECONDS"] == "300"
    assert env["XANAX_IMAGE_CUT_SKIP_MEMORY_CHECK"] == "1"
    assert env["RIENG"] == "1"
