"""
Auth routes: login, logout, session check.
"""
from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from hub.config import settings
from hub.database import (
    COOKIE_NAME,
    authenticate,
    create_session,
    delete_session,
    validate_session,
)

logger = logging.getLogger("xanax.auth")
router = APIRouter()


@dataclass
class _FailureState:
    failures: deque[float] = field(default_factory=deque)
    blocked_until: float = 0.0


class LoginRateLimiter:
    """Bộ giới hạn đăng nhập trong RAM cho mô hình chạy một process."""

    def __init__(self) -> None:
        self._by_pair: dict[tuple[str, str], _FailureState] = {}
        self._by_ip: dict[str, _FailureState] = {}

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    def reset(self) -> None:
        self._by_pair.clear()
        self._by_ip.clear()

    def retry_after(self, ip: str, username: str) -> int:
        now = self._now()
        pair = (ip, username.casefold())
        retry = max(
            self._remaining(self._by_pair.get(pair), now),
            self._remaining(self._by_ip.get(ip), now),
        )
        return math.ceil(retry) if retry > 0 else 0

    def record_failure(self, ip: str, username: str) -> int:
        now = self._now()
        self._cleanup(now)
        pair = (ip, username.casefold())
        retry = max(
            self._record(self._by_pair, pair, now),
            self._record(self._by_ip, ip, now),
        )
        return math.ceil(retry) if retry > 0 else 0

    def record_success(self, ip: str, username: str) -> None:
        self._by_pair.pop((ip, username.casefold()), None)
        self._by_ip.pop(ip, None)

    @staticmethod
    def _remaining(state: _FailureState | None, now: float) -> float:
        if state is None:
            return 0.0
        return max(0.0, state.blocked_until - now)

    def _record(self, store: dict, key, now: float) -> float:
        state = store.setdefault(key, _FailureState())
        cutoff = now - settings.login_rate_limit_window_seconds
        while state.failures and state.failures[0] <= cutoff:
            state.failures.popleft()
        state.failures.append(now)
        if len(state.failures) >= settings.login_rate_limit_attempts:
            state.blocked_until = max(
                state.blocked_until,
                now + settings.login_rate_limit_lock_seconds,
            )
        return self._remaining(state, now)

    def _cleanup(self, now: float) -> None:
        cutoff = now - settings.login_rate_limit_window_seconds
        for store in (self._by_pair, self._by_ip):
            expired = []
            for key, state in store.items():
                while state.failures and state.failures[0] <= cutoff:
                    state.failures.popleft()
                if not state.failures and state.blocked_until <= now:
                    expired.append(key)
            for key in expired:
                del store[key]


login_rate_limiter = LoginRateLimiter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    username = req.username.strip()
    client_ip = _client_ip(request)
    retry_after = login_rate_limiter.retry_after(client_ip, username)
    if retry_after:
        raise _rate_limit_error(retry_after)

    user = await authenticate(username, req.password)
    if not user:
        retry_after = login_rate_limiter.record_failure(client_ip, username)
        if retry_after:
            raise _rate_limit_error(retry_after)
        raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không đúng")

    login_rate_limiter.record_success(client_ip, username)
    token = await create_session(user["id"])
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        # Cookie phiên chết khi đóng trình duyệt, nhưng Chrome/Edge có thể khôi phục
        # nó cùng tab; bảo vệ thật vì thế nằm ở idle timeout phía server.
        path="/",
        secure=settings.secure_cookie_enabled,
    )
    logger.info("User '%s' logged in", user["username"])
    return {"ok": True, "username": user["username"]}


def _client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            first_ip = forwarded_for.split(",", 1)[0].strip()
            if first_ip:
                return first_ip
    return request.client.host if request.client else "unknown"


def _rate_limit_error(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail="Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau.",
        headers={"Retry-After": str(max(1, retry_after))},
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await delete_session(token)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def me(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await validate_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return {"username": user["username"]}
