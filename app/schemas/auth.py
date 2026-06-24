from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── Request ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8)
    email: EmailStr | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ── Response ───────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    username: str
    email: str | None
    role: str
    created_at: datetime


class WorkspaceUserOut(BaseModel):
    id: str
    username: str
    role: str


class LoginContextOut(BaseModel):
    redirect_to: str
    workspace_ready: bool = True
    user: WorkspaceUserOut


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: str
    redirect_to: str = "/workspace"
    user: WorkspaceUserOut | None = None


class AccessTokenOut(BaseModel):
    access_token: str
    expires_in: str
