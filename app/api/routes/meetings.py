from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.meeting import conductor, reporter, room as room_mod
from app.schemas.meeting import (
    MeetingReportOut, MeetingRoomOut, MeetingTurnOut,
    OpenRoomRequest, WriteReportRequest,
)

router = APIRouter()


@router.post("/", response_model=MeetingRoomOut, status_code=status.HTTP_201_CREATED)
async def open_meeting(body: OpenRoomRequest, db: AsyncSession = Depends(get_db)):
    return await room_mod.open_room(db, body.session_id, body.title, body.objective)


@router.post("/{meeting_id}/close", response_model=MeetingRoomOut)
async def close_meeting(meeting_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return await room_mod.close_room(db, meeting_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{meeting_id}/turns", response_model=list[MeetingTurnOut])
async def list_turns(meeting_id: str, db: AsyncSession = Depends(get_db)):
    return await conductor.get_turns(db, meeting_id)


@router.post("/{meeting_id}/report", response_model=MeetingReportOut, status_code=status.HTTP_201_CREATED)
async def create_report(meeting_id: str, body: WriteReportRequest, db: AsyncSession = Depends(get_db)):
    return await reporter.write_report(db, {
        "meeting_id": meeting_id,
        "author_id": body.author_id,
        "summary": body.summary,
        "decisions": body.decisions,
        "action_items": body.action_items,
    })
