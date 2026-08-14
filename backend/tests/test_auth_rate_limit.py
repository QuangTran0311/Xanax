import pytest
from httpx import ASGITransport, AsyncClient

from api.routes import auth
from hub.config import settings
from hub.server import create_app


@pytest.fixture
async def rate_client(monkeypatch):
    now = [1_000.0]
    auth.login_rate_limiter.reset()
    monkeypatch.setattr(auth.login_rate_limiter, "_now", lambda: now[0])
    monkeypatch.setattr(settings, "login_rate_limit_attempts", 3)
    monkeypatch.setattr(settings, "login_rate_limit_window_seconds", 60)
    monkeypatch.setattr(settings, "login_rate_limit_lock_seconds", 60)

    async def fake_authenticate(username, password):
        if username == "dung" and password == "mat-khau-dung":
            return {"id": 1, "username": username}
        return None

    async def fake_create_session(_user_id):
        return "test-session"

    monkeypatch.setattr(auth, "authenticate", fake_authenticate)
    monkeypatch.setattr(auth, "create_session", fake_create_session)

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, now
    auth.login_rate_limiter.reset()


async def _login(
    client,
    username="sai",
    password="sai",
    forwarded_for="203.0.113.10, 10.0.0.2",
):
    return await client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"X-Forwarded-For": forwarded_for},
    )


@pytest.mark.asyncio
async def test_locks_on_nth_failed_login_and_returns_retry_after(rate_client):
    client, _now = rate_client
    assert (await _login(client)).status_code == 401
    assert (await _login(client)).status_code == 401

    response = await _login(client)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert "thử lại sau" in response.json()["detail"]
    assert (await _login(client)).status_code == 429


@pytest.mark.asyncio
async def test_allows_login_attempt_after_window_and_lock_expire(rate_client):
    client, now = rate_client
    for _ in range(3):
        response = await _login(client)
    assert response.status_code == 429

    now[0] += 61
    assert (await _login(client)).status_code == 401


@pytest.mark.asyncio
async def test_successful_login_resets_pair_and_ip_counters(rate_client):
    client, _now = rate_client
    assert (await _login(client, "dung", "sai")).status_code == 401
    assert (await _login(client, "dung", "sai")).status_code == 401
    assert (await _login(client, "dung", "mat-khau-dung")).status_code == 200

    assert (await _login(client, "dung", "sai")).status_code == 401
    assert (await _login(client, "tai-khoan-khac", "sai")).status_code == 401


@pytest.mark.asyncio
async def test_ip_limit_aggregates_failures_across_usernames(rate_client):
    client, _now = rate_client
    assert (await _login(client, "mot")).status_code == 401
    assert (await _login(client, "hai")).status_code == 401
    assert (await _login(client, "ba")).status_code == 429


@pytest.mark.asyncio
async def test_ignores_forwarded_for_when_proxy_headers_are_untrusted(
    rate_client, monkeypatch
):
    client, _now = rate_client
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    monkeypatch.setattr(settings, "login_rate_limit_attempts", 2)

    assert (await _login(client, forwarded_for="203.0.113.10")).status_code == 401
    assert (await _login(client, forwarded_for="198.51.100.20")).status_code == 429


@pytest.mark.asyncio
async def test_uses_forwarded_for_when_proxy_headers_are_trusted(rate_client, monkeypatch):
    client, _now = rate_client
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    monkeypatch.setattr(settings, "login_rate_limit_attempts", 2)

    assert (await _login(client, forwarded_for="203.0.113.10")).status_code == 401
    assert (await _login(client, forwarded_for="198.51.100.20")).status_code == 401
    assert (await _login(client, forwarded_for="203.0.113.10")).status_code == 429


@pytest.mark.asyncio
async def test_login_cookie_uses_resolved_secure_setting(rate_client, monkeypatch):
    client, _now = rate_client
    monkeypatch.setattr(settings, "cookie_secure", True)

    response = await _login(client, "dung", "mat-khau-dung")
    assert response.status_code == 200
    assert "Secure" in response.headers["Set-Cookie"]
