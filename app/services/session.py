from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.conversation import ChatSession, Message
from app.utils.logger import logger


async def create_session(db: AsyncSession, user_id: str, title: str | None = None) -> ChatSession:
    session = ChatSession(user_id=user_id, title=title, status="active")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.debug(f"Session created: {session.id}")
    return session


async def end_session(db: AsyncSession, session_id: str) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")
    session.status = "ended"
    session.ended_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: str) -> ChatSession | None:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .options(selectinload(ChatSession.messages))
    )
    return result.scalar_one_or_none()


async def get_messages(db: AsyncSession, session_id: str) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.sequence_no)
    )
    return list(result.scalars().all())
