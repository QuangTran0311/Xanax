from datetime import datetime

from pydantic import BaseModel


# ── Request ────────────────────────────────────────────────────────────────────

class OpenRoomRequest(BaseModel):
    session_id: str
    title: str
    objective: str | None = None


class WriteReportRequest(BaseModel):
    author_id: str
    summary: str | None = None
    decisions: str | None = None
    action_items: str | None = None


# ── Response ───────────────────────────────────────────────────────────────────

class MeetingRoomOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    session_id: str
    title: str
    objective: str | None
    status: str
    opened_at: datetime
    closed_at: datetime | None


class MeetingTurnOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    meeting_id: str
    member_id: str
    turn_no: int
    turn_type: str
    addressed_to: str | None
    content: str
    latency_ms: int | None
    cost_usd: float | None
    created_at: datetime


class MeetingReportOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    meeting_id: str
    author_id: str
    summary: str | None
    decisions: str | None
    action_items: str | None
    created_at: datetime
