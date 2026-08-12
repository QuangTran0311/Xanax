"""API Routes – Health check"""
import platform
import sys
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from hub.config import settings
from hub.events import event_bus

router = APIRouter()
_start_time = time.time()


@router.get("/health", summary="Health check")
async def health_check():
    uptime = time.time() - _start_time
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
    return {"ready": True}


def _format_uptime(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}h {m}m {sec}s"
