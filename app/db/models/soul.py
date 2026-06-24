"""
NHÓM: SOUL & LONG-TERM MEMORY
Bảng: soul_knowledge, learned_patterns, soul_update_candidates
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SoulKnowledge(Base):
    __tablename__ = "soul_knowledge"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column("agentId", String(50), default="hermes")
    category: Mapped[str] = mapped_column(String(50))
    key: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column("isActive", Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint("agentId", "key", name="soul_knowledge_agentId_key_key"),
    )


class LearnedPattern(Base):
    __tablename__ = "learned_patterns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column("agentId", String(50), default="hermes")
    pattern: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), default="auto_learned")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    use_count: Mapped[int] = mapped_column("useCount", Integer, default=0)
    last_used: Mapped[Optional[datetime]] = mapped_column("lastUsed", DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())

    update_candidates: Mapped[list[SoulUpdateCandidate]] = relationship(back_populates="source_pattern")


class SoulUpdateCandidate(Base):
    __tablename__ = "soul_update_candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column("agentId", String(50), default="hermes")
    suggested_key: Mapped[str] = mapped_column("suggestedKey", String(100))
    suggested_content: Mapped[str] = mapped_column("suggestedContent", Text)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_pattern_id: Mapped[Optional[str]] = mapped_column("sourcePatternId", ForeignKey("learned_patterns.id"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_by: Mapped[Optional[str]] = mapped_column("reviewedBy", String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column("reviewedAt", DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())

    source_pattern: Mapped[Optional[LearnedPattern]] = relationship(back_populates="update_candidates")
