from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.soul import SoulKnowledge


async def load_soul(db: AsyncSession, agent_id: str = "hermes") -> dict[str, str]:
    """Trả về toàn bộ soul knowledge dưới dạng {key: content}."""
    result = await db.execute(
        select(SoulKnowledge).where(
            SoulKnowledge.agent_id == agent_id,
            SoulKnowledge.is_active.is_(True),
        )
    )
    entries = result.scalars().all()
    return {e.key: e.content for e in entries}
