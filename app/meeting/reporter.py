from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meeting import MeetingReport
from app.utils.logger import logger


async def write_report(db: AsyncSession, data: dict) -> MeetingReport:
    report = MeetingReport(**data)
    db.add(report)
    await db.commit()
    await db.refresh(report)
    logger.debug(f"Report written for meeting {data.get('meeting_id')}")
    return report
