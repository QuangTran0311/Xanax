from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.soul import SoulKnowledge
from app.schemas.soul import SoulEntryOut, UpsertSoulRequest

router = APIRouter()

_AGENT = "hermes"


@router.get("/", response_model=list[SoulEntryOut])
async def list_soul(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SoulKnowledge).where(
            SoulKnowledge.agent_id == _AGENT,
            SoulKnowledge.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


@router.put("/{key}", response_model=SoulEntryOut)
async def upsert_soul(key: str, body: UpsertSoulRequest, db: AsyncSession = Depends(get_db)):
    stmt = (
        insert(SoulKnowledge)
        .values(agent_id=_AGENT, key=key, category=body.category, content=body.content)
        .on_conflict_do_update(
            constraint="soul_knowledge_agentId_key_key",
            set_={"content": body.content, "version": SoulKnowledge.version + 1},
        )
        .returning(SoulKnowledge)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()
