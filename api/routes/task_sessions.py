"""
Task session routes — CRUD for task runner session history.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from hub.database import (
    delete_task_session,
    get_pipeline_logs,
    get_task_session,
    list_task_sessions,
    update_task_session,
)

logger = logging.getLogger("xanax.task_sessions")
router = APIRouter()


@router.get("/sessions")
async def list_sessions():
    return {"sessions": await list_task_sessions()}


@router.get("/sessions/{session_id}")
async def get_session(session_id: int):
    session = await get_task_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Task session not found")
    return session


@router.get("/sessions/{session_id}/logs")
async def get_session_logs(session_id: int):
    return {"logs": await get_pipeline_logs(session_id)}


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: int):
    ok = await delete_task_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task session not found")
