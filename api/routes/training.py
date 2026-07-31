"""
Training session routes — CRUD + SOUL.md update.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hub.database import (
    add_training_message,
    create_training_session,
    delete_training_session,
    get_training_messages,
    get_training_session,
    list_training_sessions,
    update_training_session,
)

logger = logging.getLogger("xanax.training")
router = APIRouter()


def _soul_path() -> Path:
    """Resolve SOUL.md path at call-time — avoids stale import-time env."""
    local_app_data = (
        os.environ.get("LOCALAPPDATA")
        or os.path.expandvars("%LOCALAPPDATA%")
        or str(Path.home() / "AppData" / "Local")
    )
    return Path(local_app_data) / "hermes" / "SOUL.md"


# ── Schemas ────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    title: str
    task_description: str = ""


class UpdateSessionRequest(BaseModel):
    status: str | None = None          # 'in_progress' | 'pass' | 'fail'
    result_notes: str | None = None
    title: str | None = None
    task_description: str | None = None


class AppendSoulRequest(BaseModel):
    content: str   # text to append under "## Ghi chú từ các session training"


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions():
    return {"sessions": await list_training_sessions()}


@router.post("/sessions", status_code=201)
async def create_session(req: CreateSessionRequest):
    sid = await create_training_session(req.title, req.task_description)
    session = await get_training_session(sid)
    return session


@router.get("/sessions/{session_id}")
async def get_session(session_id: int):
    session = await get_training_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await get_training_messages(session_id)
    return {**session, "messages": messages}


@router.patch("/sessions/{session_id}")
async def update_session(session_id: int, req: UpdateSessionRequest):
    ok = await update_training_session(
        session_id,
        status=req.status,
        result_notes=req.result_notes,
        title=req.title,
        task_description=req.task_description,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return await get_training_session(session_id)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: int):
    ok = await delete_training_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")


# ── SOUL.md ────────────────────────────────────────────────────────────────

@router.get("/soul")
async def get_soul():
    p = _soul_path()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"SOUL.md not found at: {p}")
    return {"content": p.read_text(encoding="utf-8")}


@router.post("/soul/append")
async def append_to_soul(req: AppendSoulRequest):
    p = _soul_path()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"SOUL.md not found at: {p}")

    try:
        current = p.read_text(encoding="utf-8")
        marker  = "## Ghi chú từ các session training"

        if marker in current:
            idx     = current.index(marker) + len(marker)
            updated = current[:idx] + "\n" + req.content.strip() + "\n" + current[idx:]
        else:
            updated = current.rstrip() + f"\n\n{marker}\n{req.content.strip()}\n"

        p.write_text(updated, encoding="utf-8")
        logger.info("SOUL.md updated at %s", p)
        return {"ok": True, "path": str(p)}
    except Exception as e:
        logger.exception("Failed to write SOUL.md at %s", p)
        raise HTTPException(status_code=500, detail=str(e))
