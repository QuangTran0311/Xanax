"""
NHÓM: AUTH
Bảng: users, user_sessions
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.conversation import ChatSession


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(100), unique=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column("passwordHash", String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="owner")
    is_active: Mapped[bool] = mapped_column("isActive", Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    sessions: Mapped[list[ChatSession]] = relationship(back_populates="user")
    user_sessions: Mapped[list[UserSession]] = relationship(back_populates="user")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("users.id"))
    refresh_token: Mapped[str] = mapped_column("refreshToken", String(512), unique=True)
    user_agent: Mapped[Optional[str]] = mapped_column("userAgent", String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column("ipAddress", String(45), nullable=True)
    expires_at: Mapped[datetime] = mapped_column("expiresAt", DateTime)
    revoked_at: Mapped[Optional[datetime]] = mapped_column("revokedAt", DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="user_sessions")
