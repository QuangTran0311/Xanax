from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.session import CreateSessionRequest, SessionOut
from app.services import session as session_service

router = APIRouter()


@router.post("/", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(body: CreateSessionRequest, db: AsyncSession = Depends(get_db)):
    return await session_service.create_session(db, body.user_id, body.title)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await session_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.post("/{session_id}/end", response_model=SessionOut)
async def end_session(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return await session_service.end_session(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
