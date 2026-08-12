"""
Chat API routes - session management and message history for the UI.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.hermes_bridge import hermes

logger = logging.getLogger("xanax.api.chat")
router = APIRouter()


class CreateSessionRequest(BaseModel):
    title: str = "Xanax Chat"


class ChatRequest(BaseModel):
    message: str
    session_id: str


@router.get("/sessions")
async def list_sessions():
    """List all local chat sessions."""
    try:
        sessions = await hermes.list_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.exception("list_sessions failed")
        raise HTTPException(status_code=502, detail=f"Hermes chat backend error: {e}")


@router.post("/sessions")
async def create_session(req: CreateSessionRequest):
    """Create a new chat session."""
    try:
        session_id = await hermes.create_session(title=req.title)
        return {"session_id": session_id, "title": req.title}
    except Exception as e:
        logger.exception("create_session failed")
        raise HTTPException(status_code=502, detail=f"Hermes chat backend error: {e}")


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get details of a specific session."""
    session = await hermes.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    """Get message history for a session."""
    try:
        messages = await hermes.get_messages(session_id)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Hermes chat backend error: {e}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    success = await hermes.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or already deleted")
    return {"deleted": session_id}


@router.get("/hermes/status")
async def hermes_status():
    """Check if the Hermes-backed chat endpoint is reachable."""
    alive = await hermes.is_alive()
    return {
        "hermes_online": alive,
        "gateway_url": hermes.base_url,
        "message": "Hermes chat backend is ready" if alive else "Hermes chat backend is offline or not configured",
    }
