"""API Routes – Health check"""
import asyncio
import platform
import logging
import re
import sys
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from hub.config import settings
from hub.database import list_model_pool
from hub.events import event_bus
from core.model_pool_bridge import CLI_API_STYLES, test_model_connection

router = APIRouter()
logger = logging.getLogger("xanax.health")
# Dùng monotonic để NTP chỉnh lùi giờ sau khi service đã chạy không làm uptime âm.
_start_time = time.monotonic()

# Probe này chỉ cần biết credential còn dùng được, không phải chờ một
# lượt suy luận đầy đủ. Timeout chung của agent là 600 giây thì quá dài
# cho monitoring; curl phía ngoài chừa thêm 15 giây cho HTTP/serialize.
_PROVIDER_TIMEOUT_SECONDS = 30.0


@router.get("/health", summary="Health check")
async def health_check():
    uptime = max(0.0, time.monotonic() - _start_time)
    return {
        "status": "ok",
        "service": settings.title,
        "version": settings.version,
        "uptime_seconds": round(uptime, 2),
        "uptime_human": _format_uptime(uptime),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system": {
            "os": platform.system(),
            "python": sys.version.split()[0],
        },
        "event_history_count": len(event_bus.get_history()),
    }


@router.get("/health/ready", summary="Readiness probe")
async def readiness():
    checks: dict[str, bool] = {}

    try:
        from hub import database

        async with database.connect() as db:
            async with db.execute("SELECT 1") as cursor:
                row = await cursor.fetchone()
        checks["database"] = bool(row and row[0] == 1)
    except Exception:
        logger.exception("Readiness database check failed")
        checks["database"] = False

    from core.orchestrator import orchestrator
    from core.scheduler import task_scheduler

    checks["orchestrator"] = orchestrator.started
    checks["scheduler"] = task_scheduler.scheduler_running
    checks["task_queue"] = task_scheduler.worker_pool_running

    ready = all(checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"ready": ready, "checks": checks},
    )


def _safe_provider_error(message: object, entry: dict) -> str:
    """Rút gọn lỗi CLI mà không mang token/đường credential ra API."""
    text = " ".join(str(message or "").split())

    config_dir = str(entry.get("cli_config_dir") or "").strip()
    if config_dir:
        text = text.replace(config_dir, "<thư mục credential>")

    text = re.sub(r"(?i)(bearer\s+)[^\s,;]+", r"\1<đã che>", text)
    text = re.sub(
        r"(?i)\b((?:[a-z0-9]+_)*(?:api[_-]?key|auth[_-]?token|token|secret|password))"
        r"\b\s*[:=]\s*[^\s,;]+",
        r"\1=<đã che>",
        text,
    )
    text = re.sub(
        r"(?i)(?:[a-z]:\\users\\[^\\\s]+\\|/home/[^/\s]+/)?\.(?:claude|codex)(?:[/\\][^\s,;:]*)*",
        "<đường dẫn credential>",
        text,
    )
    return text[:180] or "CLI báo lỗi nhưng không có thông điệp"


async def _probe_cli_provider(entry: dict) -> dict:
    base = {
        "id": entry["id"],
        "name": entry["name"],
        "api_style": entry["api_style"],
    }
    try:
        result = await asyncio.wait_for(
            test_model_connection(entry["id"]),
            timeout=_PROVIDER_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return {
            **base,
            "ok": False,
            "error": f"Quá {_PROVIDER_TIMEOUT_SECONDS:g} giây, đã hủy phép thử",
        }
    except Exception as exc:
        # Không log str(exc): exception từ CLI có thể chứa token hoặc HOME.
        logger.warning(
            "Provider check entry %s hỏng ngoài dự kiến (%s)",
            entry["id"],
            type(exc).__name__,
        )
        return {**base, "ok": False, "error": "Lỗi nội bộ khi gọi CLI"}

    if result.get("ok"):
        return {**base, "ok": True}
    return {
        **base,
        "ok": False,
        "error": _safe_provider_error(result.get("error"), entry),
    }


@router.post("/health/providers", summary="Kiểm tra credential CLI provider")
async def provider_health():
    """Gọi thật các model CLI; AuthGuard giữ route này không công khai."""
    entries = [
        entry
        for entry in await list_model_pool()
        if entry.get("api_style") in CLI_API_STYLES
    ]

    # Chạy song song để trần thời gian của endpoint vẫn xấp xỉ 30 giây,
    # không thành 30 giây × số entry khi nhiều credential cùng hết hạn.
    results = await asyncio.gather(*(_probe_cli_provider(entry) for entry in entries))
    failures = [result for result in results if not result["ok"]]
    ok = not failures
    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "ok": ok,
            "total": len(entries),
            "failures": failures,
            "results": results,
        },
    )


def _format_uptime(seconds: float) -> str:
    s = max(0, int(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}h {m}m {sec}s"
