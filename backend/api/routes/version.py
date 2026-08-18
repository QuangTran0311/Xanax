"""Phiên bản đang chạy và mã nguồn tương ứng, với mức lộ thông tin theo xác thực."""
from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Request

from hub.config import settings

router = APIRouter()
_REPO_ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def get_git_commit() -> str | None:
    """Đọc Git đúng một lần; bản tarball không có repository vẫn khởi động được."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    commit = completed.stdout.strip()
    return commit or None


@router.get("/version", summary="Phiên bản ứng dụng đang chạy")
async def current_version(request: Request):
    result: dict[str, str | None] = {"version": settings.version}
    # Commit là dấu vân tay triển khai: chỉ AuthGuard mới được đánh dấu request
    # đã xác thực; người ngoài chỉ cần số phiên bản để vẽ trang đăng nhập.
    if request.scope.get("authenticated"):
        result["commit"] = get_git_commit()
    return result
