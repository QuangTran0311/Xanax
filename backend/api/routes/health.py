"""API Routes – Health check"""
import platform
import logging
import sys
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from hub.config import settings
from hub.events import event_bus

router = APIRouter()
logger = logging.getLogger("xanax.health")
# Dùng monotonic để NTP chỉnh lùi giờ sau khi service đã chạy không làm uptime âm.
_start_time = time.monotonic()


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


def _format_uptime(seconds: float) -> str:
    s = max(0, int(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}h {m}m {sec}s"
