"""
NHÓM: MODEL INTELLIGENCE
Bảng: model_registry, model_usage_logs, model_scores, routing_rules
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
    from app.db.models.conversation import ChatSession, ToolCall
    from app.db.models.meeting import MeetingMember


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    model_id: Mapped[str] = mapped_column("modelId", String(100), primary_key=True)
    provider: Mapped[str] = mapped_column(String(50))
    modality: Mapped[str] = mapped_column(String(20))
    sub_types: Mapped[list[str]] = mapped_column("subTypes", ARRAY(String), default=list)
    context_window: Mapped[Optional[int]] = mapped_column("contextWindow", Integer, nullable=True)
    supports_stream: Mapped[bool] = mapped_column("supportsStream", Boolean, default=True)
    input_formats: Mapped[list[str]] = mapped_column("inputFormats", ARRAY(String), default=list)
    output_formats: Mapped[list[str]] = mapped_column("outputFormats", ARRAY(String), default=list)
    cost_per_1k_input: Mapped[Optional[float]] = mapped_column("costPer1kInput", Float, nullable=True)
    cost_per_1k_output: Mapped[Optional[float]] = mapped_column("costPer1kOutput", Float, nullable=True)
    cost_per_unit: Mapped[Optional[float]] = mapped_column("costPerUnit", Float, nullable=True)
    api_endpoint: Mapped[Optional[str]] = mapped_column("apiEndpoint", String, nullable=True)
    api_key_ref: Mapped[Optional[str]] = mapped_column("apiKeyRef", String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column("isActive", Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column("addedAt", DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime, server_default=func.now(), onupdate=func.now())

    usage_logs: Mapped[list[ModelUsageLog]] = relationship(back_populates="model")
    scores: Mapped[list[ModelScore]] = relationship(back_populates="model")
    meeting_members: Mapped[list[MeetingMember]] = relationship(back_populates="model")


class ModelUsageLog(Base):
    __tablename__ = "model_usage_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column("sessionId", ForeignKey("sessions.id"))
    tool_call_id: Mapped[Optional[str]] = mapped_column("toolCallId", ForeignKey("tool_calls.id"), nullable=True)
    model_id: Mapped[str] = mapped_column("modelId", ForeignKey("model_registry.modelId"), nullable=False)
    task_type: Mapped[str] = mapped_column("taskType", String(50))
    input_tokens: Mapped[Optional[int]] = mapped_column("inputTokens", Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column("outputTokens", Integer, nullable=True)
    input_chars: Mapped[Optional[int]] = mapped_column("inputChars", Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column("latencyMs", Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column("costUsd", Float, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_msg: Mapped[Optional[str]] = mapped_column("errorMsg", Text, nullable=True)
    user_rating: Mapped[Optional[int]] = mapped_column("userRating", Integer, nullable=True)
    auto_quality: Mapped[Optional[float]] = mapped_column("autoQuality", Float, nullable=True)
    feedback_note: Mapped[Optional[str]] = mapped_column("feedbackNote", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="model_usage_logs")
    tool_call: Mapped[Optional[ToolCall]] = relationship(back_populates="model_usage_logs")
    model: Mapped[ModelRegistry] = relationship(back_populates="usage_logs")


class ModelScore(Base):
    __tablename__ = "model_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    model_id: Mapped[str] = mapped_column("modelId", ForeignKey("model_registry.modelId"))
    task_type: Mapped[str] = mapped_column("taskType", String(50))
    avg_latency_ms: Mapped[float] = mapped_column("avgLatencyMs", Float, default=0.0)
    avg_cost_usd: Mapped[float] = mapped_column("avgCostUsd", Float, default=0.0)
    success_rate: Mapped[float] = mapped_column("successRate", Float, default=1.0)
    quality_score: Mapped[float] = mapped_column("qualityScore", Float, default=0.5)
    sample_count: Mapped[int] = mapped_column("sampleCount", Integer, default=0)
    final_score: Mapped[float] = mapped_column("finalScore", Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime, server_default=func.now(), onupdate=func.now())

    model: Mapped[ModelRegistry] = relationship(back_populates="scores")

    __table_args__ = (
        # Unique constraint: one score record per (model, task_type)
        __import__("sqlalchemy").UniqueConstraint("modelId", "taskType", name="model_scores_modelId_taskType_key"),
    )


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    rule_name: Mapped[str] = mapped_column("ruleName", String(100), unique=True)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    modality: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    conditions: Mapped[dict[str, Any]] = mapped_column(JSON)
    preferred_models: Mapped[list[str]] = mapped_column("preferredModels", ARRAY(String), default=list)
    excluded_models: Mapped[list[str]] = mapped_column("excludedModels", ARRAY(String), default=list)
    override_score: Mapped[bool] = mapped_column("overrideScore", Boolean, default=False)
    is_active: Mapped[bool] = mapped_column("isActive", Boolean, default=True)
    created_by: Mapped[str] = mapped_column("createdBy", String(20), default="human")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())
