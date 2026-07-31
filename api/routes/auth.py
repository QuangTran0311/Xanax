"""
Auth routes: login, logout, session check.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from hub.database import (
    COOKIE_NAME,
    authenticate,
    create_session,
    delete_session,
    validate_session,
)

logger = logging.getLogger("xanax.auth")
router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(req: LoginRequest, response: Response):
    user = await authenticate(req.username.strip(), req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không đúng")

    token = await create_session(user["id"])
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=604_800,  # 7 days
        path="/",
        secure=False,
    )
    logger.info("User '%s' logged in", user["username"])
    return {"ok": True, "username": user["username"]}


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
