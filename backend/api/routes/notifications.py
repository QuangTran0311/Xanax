"""REST API cho Trung tâm thông báo dùng chung của Hub."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from core.notifications import (
    public_notification,
    read_all_notifications,
    read_notification,
    resolve_one_notification,
)
from hub.database import (
    get_unread_notification_count,
    list_notifications,
)

router = APIRouter()
NotificationStatus = Literal["unread", "read", "resolved"]


@router.get("")
async def get_notifications(
    status: NotificationStatus | None = None,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    notifications, total = await list_notifications(
        status=status, limit=limit, offset=offset,
    )
    return {
        "notifications": [public_notification(item) for item in notifications],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/unread-count")
async def unread_count():
    return {"count": await get_unread_notification_count()}


@router.post("/read-all")
async def mark_all_read():
    return {
        "changed": await read_all_notifications(),
        "count": await get_unread_notification_count(),
    }


@router.post("/{notification_id}/read")
async def mark_read(notification_id: int):
    notification = await read_notification(notification_id)
    if not notification:
        raise HTTPException(404, "Notification not found")
    return notification


@router.post("/{notification_id}/resolve")
async def resolve(notification_id: int):
    notification = await resolve_one_notification(notification_id)
    if not notification:
        raise HTTPException(404, "Notification not found")
    return notification
