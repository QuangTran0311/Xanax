import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.services.auth import ensure_admin_account
from app.utils.logger import logger
from app.api.routes import auth, sessions, messages, models, soul, meetings, workspace

STATIC_DIR = Path(__file__).parent / "static"

# ── App factory ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Hermes Hub",
    version="1.0.0",
    description="AI Orchestration Server",
    docs_url="/docs" if settings.is_dev else None,
    redoc_url=None,
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────────────────

app.include_router(auth.router,     prefix="/api/auth",     tags=["auth"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(models.router,   prefix="/api/models",   tags=["models"])
app.include_router(soul.router,     prefix="/api/soul",     tags=["soul"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
app.include_router(workspace.router, prefix="/workspace", tags=["workspace"])

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def login_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "agent": "hermes", "version": "1.0.0"}


@app.on_event("startup")
async def bootstrap_admin() -> None:
    async with AsyncSessionLocal() as db:
        await ensure_admin_account(db)


# ── Entrypoint ─────────────────────────────────────────────────────────────────

def run() -> None:
    logger.info(f"Hermes Hub starting on http://localhost:{settings.port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=settings.is_dev)


if __name__ == "__main__":
    run()
