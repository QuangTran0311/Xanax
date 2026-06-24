from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.conversation import ChatSession
from app.db.models.episode import Episode
from app.utils.logger import logger


async def distill_to_episode(
    db: AsyncSession,
    session_id: str,
    reflection: str | None = None,
) -> Episode:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .options(selectinload(ChatSession.messages))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError(f"Session {session_id} not found")

    key_actions = [
        m.content or ""
        for m in session.messages
        if m.role == "assistant"
    ][:5]

    episode = Episode(
        session_id=session_id,
        task_summary=session.title or session.summary,
        key_actions=key_actions,
        outcome=session.status,
        reflection=reflection,
    )
    db.add(episode)
    await db.commit()
    await db.refresh(episode)
    logger.debug(f"Episode created for session {session_id}")
    return episode


async def list_episodes(db: AsyncSession, limit: int = 10) -> list[Episode]:
    result = await db.execute(
        select(Episode).order_by(Episode.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
