"""
NHÓM: MEETING ROOM
Bảng: agent_roles, meeting_rooms, meeting_members, meeting_turns, meeting_reports
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.conversation import ChatSession
    from app.db.models.intelligence import ModelRegistry


class AgentRole(Base):
    __tablename__ = "agent_roles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    role_code: Mapped[str] = mapped_column("roleCode", String(20), unique=True)
    role_name: Mapped[str] = mapped_column("roleName", String(100))
    expertise: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[Optional[str]] = mapped_column("systemPrompt", Text, nullable=True)
    is_active: Mapped[bool] = mapped_column("isActive", Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())

    members: Mapped[list[MeetingMember]] = relationship(back_populates="role")


class MeetingRoom(Base):
    __tablename__ = "meeting_rooms"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column("sessionId", ForeignKey("sessions.id"), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="opened")
    opened_at: Mapped[datetime] = mapped_column("openedAt", DateTime, server_default=func.now())
    closed_at: Mapped[Optional[datetime]] = mapped_column("closedAt", DateTime, nullable=True)

    session: Mapped[ChatSession] = relationship(back_populates="meeting_room")
    members: Mapped[list[MeetingMember]] = relationship(back_populates="meeting")
    turns: Mapped[list[MeetingTurn]] = relationship(back_populates="meeting", order_by="MeetingTurn.turn_no")
    reports: Mapped[list[MeetingReport]] = relationship(back_populates="meeting")


class MeetingMember(Base):
    __tablename__ = "meeting_members"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column("meetingId", ForeignKey("meeting_rooms.id"))
    model_id: Mapped[str] = mapped_column("modelId", ForeignKey("model_registry.modelId"))
    role_id: Mapped[str] = mapped_column("roleId", ForeignKey("agent_roles.id"))
    is_chair: Mapped[bool] = mapped_column("isChair", Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column("joinedAt", DateTime, server_default=func.now())

    meeting: Mapped[MeetingRoom] = relationship(back_populates="members")
    model: Mapped[ModelRegistry] = relationship(back_populates="meeting_members")
    role: Mapped[AgentRole] = relationship(back_populates="members")
    turns: Mapped[list[MeetingTurn]] = relationship(back_populates="member")
    reports_authored: Mapped[list[MeetingReport]] = relationship(back_populates="author")


class MeetingTurn(Base):
    __tablename__ = "meeting_turns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column("meetingId", ForeignKey("meeting_rooms.id"))
    member_id: Mapped[str] = mapped_column("memberId", ForeignKey("meeting_members.id"))
    turn_no: Mapped[int] = mapped_column("turnNo", Integer)
    turn_type: Mapped[str] = mapped_column("turnType", String(20))
    addressed_to: Mapped[Optional[str]] = mapped_column("addressedTo", String, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[Optional[int]] = mapped_column("latencyMs", Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column("costUsd", Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())

    meeting: Mapped[MeetingRoom] = relationship(back_populates="turns")
    member: Mapped[MeetingMember] = relationship(back_populates="turns")


class MeetingReport(Base):
    __tablename__ = "meeting_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column("meetingId", ForeignKey("meeting_rooms.id"))
    author_id: Mapped[str] = mapped_column("authorId", ForeignKey("meeting_members.id"))
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_items: Mapped[Optional[str]] = mapped_column("actionItems", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())

    meeting: Mapped[MeetingRoom] = relationship(back_populates="reports")
    author: Mapped[MeetingMember] = relationship(back_populates="reports_authored")
