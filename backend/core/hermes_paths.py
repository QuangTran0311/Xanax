"""Phân giải thư mục cấu hình dùng chung của Hermes theo hệ điều hành."""
from __future__ import annotations

import os
import platform
from pathlib import Path


def hermes_home() -> Path | None:
    """Trả về thư mục cấu hình Hermes, hoặc None nếu hệ thống không phân giải được."""
    explicit = (os.environ.get("HERMES_HOME") or "").strip()
    if explicit:
        try:
            return Path(explicit).expanduser()
        except (OSError, RuntimeError):
            return None

    if platform.system() == "Windows":
        local_app_data = (os.environ.get("LOCALAPPDATA") or "").strip()
        return Path(local_app_data) / "hermes" if local_app_data else None

    try:
        home = Path.home()
    except (OSError, RuntimeError):
        return None

    xdg_config = (os.environ.get("XDG_CONFIG_HOME") or "").strip()
    candidate = Path(xdg_config) / "hermes" if xdg_config else home / ".config" / "hermes"
    legacy = home / ".hermes"
    return legacy if not candidate.exists() and legacy.exists() else candidate
