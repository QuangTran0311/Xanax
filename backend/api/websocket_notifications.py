"""Authenticated realtime channel for notification state changes."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.notifications import notification_manager
from hub.database import get_unread_notification_count

logger = logging.getLogger("xanax.ws.notifications")
router = APIRouter()


@router.websocket("/ws/notifications")
async def notifications_ws(ws: WebSocket):
    await ws.accept()
    queue = notification_manager.subscribe()
    try:
        await ws.send_json({
            "type": "snapshot",
            "unread_count": await get_unread_notification_count(),
        })
        while True:
            event_task = asyncio.create_task(queue.get())
            receive_task = asyncio.create_task(ws.receive_json())
            done, pending = await asyncio.wait(
                {event_task, receive_task}, return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            if event_task in done:
                await ws.send_json(event_task.result())
            if receive_task in done:
                message = receive_task.result()
                if isinstance(message, dict) and message.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info("Notification WebSocket client disconnected")
    except Exception:
        logger.exception("Notification WebSocket failed")
    finally:
        notification_manager.unsubscribe(queue)
