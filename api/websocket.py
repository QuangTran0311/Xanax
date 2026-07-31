"""
WebSocket endpoint – Real-time streaming chat proxy between Xanax UI and Hermes.

Protocol:
  Client → Server:  JSON { "message": "...", "session_id": "..." }
  Server → Client:  JSON chunks:
    { "type": "chunk",  "content": "..." }   – streaming text token
    { "type": "done" }                        – response complete
    { "type": "error", "message": "..." }     – error occurred
    { "type": "status", "status": "..." }     – agent status updates
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from core.hermes_bridge import hermes

logger = logging.getLogger("xanax.websocket")
router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat with Hermes.

    The client sends:
      { "message": "...", "session_id": "..." }

    The server streams response chunks back, then sends { "type": "done" }.
    """
    await websocket.accept()
    logger.info("WebSocket chat client connected")

    try:
        while True:
            # Wait for client message
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await _send(websocket, {"type": "error", "message": "Invalid JSON"})
                continue

            message = data.get("message", "").strip()
            session_id = data.get("session_id", "")

            if not message:
                await _send(websocket, {"type": "error", "message": "Empty message"})
                continue

            if not session_id:
                await _send(websocket, {"type": "error", "message": "Missing session_id"})
                continue

            # Check the Hermes-backed chat endpoint is alive
            if not await hermes.is_alive():
                await _send(websocket, {
                    "type": "error",
                    "message": "Hermes chat backend is offline or not configured"
                })
                continue

            # Stream response from Hermes
            await _send(websocket, {"type": "status", "status": "thinking"})
            token_count = 0
            try:
                async for chunk in hermes.chat_stream(session_id, message):
                    if websocket.client_state != WebSocketState.CONNECTED:
                        break
                    await _send(websocket, {"type": "chunk", "content": chunk})
                    token_count += 1

                await _send(websocket, {"type": "done", "tokens": token_count})
                logger.debug("Chat complete: %d tokens for session %s", token_count, session_id[:8])

            except Exception as e:
                logger.exception("Streaming error for session %s", session_id)
                await _send(websocket, {"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await _send(websocket, {"type": "error", "message": str(e)})
        except Exception:
            pass


async def _send(ws: WebSocket, data: dict) -> None:
    """Send JSON to the WebSocket client (silently ignore if disconnected)."""
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass
