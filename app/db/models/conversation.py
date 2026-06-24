"""
NHÓM: CONVERSATION CORE
Bảng: sessions, messages, tool_calls, artifacts, execution_logs
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.auth import User
    from app.db.models.intelligence import ModelUsageLog
    from app.db.models.episode import Episode
    from app.db.models.meeting import MeetingRoom


class ChatSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("users.id"))
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    started_at: Mapped[datetime] = mapped_column("startedAt", DateTime, server_default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column("endedAt", DateTime, nullable=True)
    total_messages: Mapped[int] = mapped_column("totalMessages", Integer, default=0)
    total_tool_calls: Mapped[int] = mapped_column("totalToolCalls", Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column("totalCostUsd", Float, default=0.0)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="sessions")
    messages: Mapped[list[Message]] = relationship(back_populates="session", order_by="Message.sequence_no")
    tool_calls: Mapped[list[ToolCall]] = relationship(back_populates="session")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="session")
    execution_logs: Mapped[list[ExecutionLog]] = relationship(back_populates="session")
    model_usage_logs: Mapped[list[ModelUsageLog]] = relationship(back_populates="session")
    episode: Mapped[Optional[Episode]] = relationship(back_populates="session", uselist=False)
    meeting_room: Mapped[Optional[MeetingRoom]] = relationship(back_populates="session", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column("sessionId", ForeignKey("sessions.id"))
    sequence_no: Mapped[int] = mapped_column("sequenceNo", Integer)
    role: Mapped[str] = mapped_column(String(20))
    content_type: Mapped[str] = mapped_column("contentType", String(30), default="text")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    artifact_id: Mapped[Optional[str]] = mapped_column("artifactId", String, nullable=True)
    model_id: Mapped[Optional[str]] = mapped_column("modelId", String(100), nullable=True)
    input_tokens: Mapped[Optional[int]] = mapped_column("inputTokens", Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column("outputTokens", Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column("costUsd", Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="messages")
    tool_calls: Mapped[list[ToolCall]] = relationship(back_populates="message")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column("sessionId", ForeignKey("sessions.id"))
    message_id: Mapped[str] = mapped_column("messageId", ForeignKey("messages.id"))
    sequence_no: Mapped[int] = mapped_column("sequenceNo", Integer)
    tool_name: Mapped[str] = mapped_column("toolName", String(100))
    input_params: Mapped[Optional[dict[str, Any]]] = mapped_column("inputParams", JSON, nullable=True)
    output_result: Mapped[Optional[dict[str, Any]]] = mapped_column("outputResult", JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_msg: Mapped[Optional[str]] = mapped_column("errorMsg", Text, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column("latencyMs", Integer, nullable=True)
    cost_usd: Mapped[float] = mapped_column("costUsd", Float, default=0.0)
    called_at: Mapped[datetime] = mapped_column("calledAt", DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column("completedAt", DateTime, nullable=True)

    session: Mapped[ChatSession] = relationship(back_populates="tool_calls")
    message: Mapped[Message] = relationship(back_populates="tool_calls")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="tool_call")
    execution_logs: Mapped[list[ExecutionLog]] = relationship(back_populates="tool_call")
    model_usage_logs: Mapped[list[ModelUsageLog]] = relationship(back_populates="tool_call")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column("sessionId", ForeignKey("sessions.id"))
    tool_call_id: Mapped[Optional[str]] = mapped_column("toolCallId", ForeignKey("tool_calls.id"), nullable=True)
    artifact_type: Mapped[str] = mapped_column("artifactType", String(30))
    file_name: Mapped[Optional[str]] = mapped_column("fileName", String(255), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column("mimeType", String(100), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column("sizeBytes", Integer, nullable=True)
    storage_ref: Mapped[str] = mapped_column("storageRef", String)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_deleted: Mapped[bool] = mapped_column("isDeleted", Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="artifacts")
    tool_call: Mapped[Optional[ToolCall]] = relationship(back_populates="artifacts")


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column("sessionId", ForeignKey("sessions.id"))
    tool_call_id: Mapped[Optional[str]] = mapped_column("toolCallId", ForeignKey("tool_calls.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(10))
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    logged_at: Mapped[datetime] = mapped_column("loggedAt", DateTime, server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="execution_logs")
    tool_call: Mapped[Optional[ToolCall]] = relationship(back_populates="execution_logs")

