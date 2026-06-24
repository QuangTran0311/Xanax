"""
NHÓM: EPISODIC MEMORY
Bảng: episodes
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.conversation import ChatSession


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column("sessionId", ForeignKey("sessions.id"), unique=True)
    agent_id: Mapped[str] = mapped_column("agentId", String(50), default="hermes")
    task_summary: Mapped[Optional[str]] = mapped_column("taskSummary", Text, nullable=True)
    key_actions: Mapped[list[str]] = mapped_column("keyActions", ARRAY(String), default=list)
    outcome: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    user_rating: Mapped[Optional[int]] = mapped_column("userRating", Integer, nullable=True)
    reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="episode")
