from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from api.routes import auth
from hub import database
from hub.config import settings
from hub.server import create_app


@pytest.fixture(autouse=True)
def fixed_session_limits(monkeypatch):
    monkeypatch.setattr(settings, "session_idle_timeout_minutes", 30)
    monkeypatch.setattr(settings, "session_absolute_hours", 8)


@pytest.fixture
async def session_user_id():
    return await database.create_user("session-test-user", "test-password")


def _utc_text(delta: timedelta = timedelta()) -> str:
    return (datetime.now(timezone.utc) + delta).strftime("%Y-%m-%d %H:%M:%S")


async def _set_session_times(
    token: str,
    *,
    last_seen_at: str | None = None,
    expires_at: str | None = None,
) -> None:
    assignments = []
    values = []
    if last_seen_at is not None:
        assignments.append("last_seen_at = ?")
        values.append(last_seen_at)
    if expires_at is not None:
        assignments.append("expires_at = ?")
        values.append(expires_at)
    async with database.connect() as db:
        await db.execute(
            f"UPDATE sessions SET {', '.join(assignments)} WHERE token = ?",
            (*values, token),
        )
        await db.commit()


async def _session_times(token: str) -> tuple[str, str] | None:
    async with database.connect() as db:
        async with db.execute(
            "SELECT expires_at, last_seen_at FROM sessions WHERE token = ?",
            (token,),
        ) as cur:
            return await cur.fetchone()


@pytest.mark.asyncio
async def test_new_session_is_valid(session_user_id):
    token = await database.create_session(session_user_id)

    user = await database.validate_session(token)

    assert user == {"id": session_user_id, "username": "session-test-user"}


@pytest.mark.asyncio
async def test_session_older_than_idle_timeout_is_invalid(session_user_id):
    token = await database.create_session(session_user_id)
    await _set_session_times(
        token,
        last_seen_at=_utc_text(-timedelta(minutes=31)),
    )

    assert await database.validate_session(token) is None


@pytest.mark.asyncio
async def test_activity_within_idle_timeout_advances_last_seen(session_user_id):
    token = await database.create_session(session_user_id)
    old_last_seen = _utc_text(-timedelta(minutes=5))
    await _set_session_times(token, last_seen_at=old_last_seen)

    user = await database.validate_session(token)
    session_times = await _session_times(token)

    assert user is not None
    assert session_times is not None
    assert session_times[1] > old_last_seen


@pytest.mark.asyncio
async def test_absolute_expiry_wins_over_fresh_last_seen(session_user_id):
    token = await database.create_session(session_user_id)
    await _set_session_times(
        token,
        expires_at=_utc_text(-timedelta(minutes=1)),
        last_seen_at=_utc_text(),
    )

    assert await database.validate_session(token) is None


@pytest.mark.asyncio
async def test_purge_removes_idle_expired_session(session_user_id):
    idle_expired = await database.create_session(session_user_id)
    still_active = await database.create_session(session_user_id)
    await _set_session_times(
        idle_expired,
        last_seen_at=_utc_text(-timedelta(minutes=31)),
    )

    await database.purge_expired_sessions()

    assert await _session_times(idle_expired) is None
    assert await _session_times(still_active) is not None


@pytest.mark.asyncio
async def test_login_cookie_has_no_max_age(monkeypatch):
    async def fake_authenticate(username, password):
        return {"id": 1, "username": username}

    async def fake_create_session(_user_id):
        return "test-session"

    monkeypatch.setattr(auth, "authenticate", fake_authenticate)
    monkeypatch.setattr(auth, "create_session", fake_create_session)

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/auth/login",
            json={"username": "dung", "password": "mat-khau-dung"},
        )

    assert response.status_code == 200
    assert "max-age" not in response.headers["Set-Cookie"].lower()
