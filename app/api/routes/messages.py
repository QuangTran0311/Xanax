from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import hermes
from app.api.deps import get_db
from app.schemas.session import ChatOut, ChatRequest, MessageOut
from app.services import session as session_service

router = APIRouter()


@router.get("/{session_id}", response_model=list[MessageOut])
async def list_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    return await session_service.get_messages(db, session_id)


@router.post("/{session_id}/chat", response_model=ChatOut)
async def chat(session_id: str, body: ChatRequest, db: AsyncSession = Depends(get_db)):
    reply = await hermes.chat(db, session_id, body.message)
    return ChatOut(reply=reply)
