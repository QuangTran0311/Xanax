from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.meeting import MeetingMember, MeetingTurn
from app.utils.logger import logger


async def add_turn(db: AsyncSession, data: dict) -> MeetingTurn:
    turn = MeetingTurn(**data)
    db.add(turn)
    await db.commit()
    await db.refresh(turn)
    return turn


async def get_turns(db: AsyncSession, meeting_id: str) -> list[MeetingTurn]:
    result = await db.execute(
        select(MeetingTurn)
        .where(MeetingTurn.meeting_id == meeting_id)
        .options(selectinload(MeetingTurn.member))
        .order_by(MeetingTurn.turn_no)
    )
    return list(result.scalars().all())
