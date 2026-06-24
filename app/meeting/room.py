from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meeting import MeetingRoom
from app.utils.logger import logger


async def open_room(
    db: AsyncSession,
    session_id: str,
    title: str,
    objective: str | None = None,
) -> MeetingRoom:
    room = MeetingRoom(session_id=session_id, title=title, objective=objective, status="opened")
    db.add(room)
    await db.commit()
    await db.refresh(room)
    logger.debug(f"Meeting opened: {room.id}")
    return room


async def close_room(db: AsyncSession, meeting_id: str) -> MeetingRoom:
    room = await db.get(MeetingRoom, meeting_id)
    if not room:
        raise ValueError(f"Meeting {meeting_id} not found")
    room.status = "closed"
    room.closed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(room)
    return room
