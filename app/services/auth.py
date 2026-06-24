from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models.auth import User, UserSession

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
WORKSPACE_ALLOWED_ROLES = {"admin", "owner"}

# ── JWT helpers ────────────────────────────────────────────────────────────────

def _parse_duration(value: str) -> timedelta:
    """Convert '15m' / '7d' / '1h' to timedelta."""
    units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
    return timedelta(**{units[value[-1]]: int(value[:-1])})


def _sign(payload: dict, secret: str, expires_in: str) -> str:
    expire = datetime.now(timezone.utc) + _parse_duration(expires_in)
    return jwt.encode({**payload, "exp": expire}, secret, algorithm="HS256")


def _utc_naive_now() -> datetime:
    return datetime.utcnow()


def create_access_token(user: User) -> str:
    return _sign(
        {"sub": user.id, "username": user.username, "role": user.role},
        settings.jwt_secret,
        settings.jwt_expires_in,
    )


def create_refresh_token(user_id: str) -> str:
    return _sign({"sub": user_id}, settings.jwt_refresh_secret, settings.jwt_refresh_expires_in)


def verify_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def _is_workspace_role(role: str | None) -> bool:
    return bool(role) and role in WORKSPACE_ALLOWED_ROLES


async def ensure_admin_account(db: AsyncSession) -> User | None:
    """Create the bootstrap admin account when credentials are provided."""
    username = settings.admin_username.strip()
    password = settings.admin_password
    if not username or not password:
        return None

    user = await db.scalar(select(User).where(User.username == username))
    if user:
        if not _is_workspace_role(user.role):
            user.role = settings.admin_role or "admin"
        if settings.admin_email and not user.email:
            user.email = settings.admin_email
        user.password_hash = pwd_context.hash(password)
        await db.commit()
        await db.refresh(user)
        return user

    user = User(
        username=username,
        email=settings.admin_email or None,
        password_hash=pwd_context.hash(password),
        role=settings.admin_role or "admin",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ── Service functions ──────────────────────────────────────────────────────────

async def register(
    db: AsyncSession,
    username: str,
    password: str,
    email: str | None = None,
) -> User:
    exists = await db.scalar(select(User).where(User.username == username))
    if exists:
        raise ValueError("Username already taken")

    user = User(
        username=username,
        email=email,
        password_hash=pwd_context.hash(password),
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login(
    db: AsyncSession,
    username: str,
    password: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> dict:
    """Return login payload with tokens and workspace redirect target."""
    user = await db.scalar(select(User).where(User.username == username))
    if not user or not user.password_hash:
        raise PermissionError("Invalid credentials")
    if not user.is_active:
        raise PermissionError("Account disabled")
    if not _is_workspace_role(user.role):
        raise PermissionError("Admin account required")
    if not pwd_context.verify(password, user.password_hash):
        raise PermissionError("Invalid credentials")

    refresh_token = create_refresh_token(user.id)
    expires_at = _utc_naive_now() + _parse_duration(settings.jwt_refresh_expires_in)

    session = UserSession(
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(session)
    await db.commit()

    return {
        "access_token": create_access_token(user),
        "refresh_token": refresh_token,
        "expires_in": settings.jwt_expires_in,
        "redirect_to": settings.workspace_path,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    }


async def refresh(db: AsyncSession, refresh_token: str) -> str:
    """Return new access_token."""
    try:
        payload = jwt.decode(refresh_token, settings.jwt_refresh_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise PermissionError("Invalid refresh token") from exc

    row = await db.scalar(select(UserSession).where(UserSession.refresh_token == refresh_token))
    if not row or row.revoked_at or row.expires_at < _utc_naive_now():
        raise PermissionError("Refresh token revoked or expired")

    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise PermissionError("User not found")
    if not _is_workspace_role(user.role):
        raise PermissionError("Admin account required")

    return create_access_token(user)


async def logout(db: AsyncSession, refresh_token: str) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.refresh_token == refresh_token, UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
