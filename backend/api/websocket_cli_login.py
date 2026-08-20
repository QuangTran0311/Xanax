"""Authenticated WebSocket transport for fixed CLI subscription login flows."""
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.cli_login import (
    LoginSessionConflict,
    LoginSessionError,
    cli_login_manager,
)
from core.provider_errors import safe_provider_error
from hub.database import get_model_pool_entry

logger = logging.getLogger("xanax.ws.cli_login")
router = APIRouter()
_TERMINAL_EVENTS = {"completed", "cancelled", "error"}


@router.websocket("/ws/cli-login/{model_pool_id}")
async def cli_login_ws(ws: WebSocket, model_pool_id: int):
    await ws.accept()
    entry = await get_model_pool_entry(model_pool_id)
    if not entry:
        await ws.send_json({"type": "error", "message": "Model not found"})
        return
    if entry.get("api_style") not in {"claude_cli", "codex_cli"}:
        await ws.send_json({"type": "error", "message": "This model does not use CLI authentication"})
        return

    session = None
    receive_task: asyncio.Task | None = None
    event_task: asyncio.Task | None = None
    try:
        session, started = await cli_login_manager.start(entry)
        await ws.send_json(started)

        while True:
            receive_task = asyncio.create_task(ws.receive_json())
            event_task = asyncio.create_task(session.next_event())
            done, pending = await asyncio.wait(
                {receive_task, event_task}, return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

            if event_task in done:
                event = event_task.result()
                await ws.send_json(event)
                if event.get("type") in _TERMINAL_EVENTS:
                    return
                if receive_task not in done:
                    continue

            message = receive_task.result()
            message_type = message.get("type") if isinstance(message, dict) else None
            if message_type == "cancel":
                await session.cancel()
            elif message_type == "submit_code" and entry.get("api_style") == "claude_cli":
                try:
                    await session.submit_code(str(message.get("code") or ""))
                except LoginSessionError as exc:
                    await ws.send_json({
                        "type": "error",
                        "message": safe_provider_error(exc, entry),
                    })
            else:
                await ws.send_json({"type": "error", "message": "Unsupported login action"})

    except WebSocketDisconnect:
        logger.info("CLI login client disconnected for model pool %s", model_pool_id)
    except LoginSessionConflict as exc:
        await ws.send_json({"type": "error", "message": safe_provider_error(exc, entry)})
    except Exception as exc:
        # Never log exception text: a CLI failure may include a token or config path.
        logger.warning(
            "CLI login failed for model pool %s (%s)", model_pool_id, type(exc).__name__,
        )
        with suppress(Exception):
            await ws.send_json({"type": "error", "message": safe_provider_error(exc, entry)})
    finally:
        for task in (receive_task, event_task):
            if task and not task.done():
                task.cancel()
        if session is not None:
            await cli_login_manager.release(model_pool_id, session)
