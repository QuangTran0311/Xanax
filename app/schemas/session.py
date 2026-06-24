from datetime import datetime
from typing import Any

from pydantic import BaseModel


# ── Request ────────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    user_id: str
    title: str | None = None


class ChatRequest(BaseModel):
    message: str


# ── Response ───────────────────────────────────────────────────────────────────

class SessionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    user_id: str
    title: str | None
    status: str
    started_at: datetime
    ended_at: datetime | None
    total_messages: int
    total_cost_usd: float
    created_at: datetime


class MessageOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    session_id: str
    sequence_no: int
    role: str
    content: str | None
    model_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    created_at: datetime


class ChatOut(BaseModel):
    reply: str
