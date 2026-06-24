from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.auth import (
    AccessTokenOut, LoginRequest, LogoutRequest,
    RefreshRequest, RegisterRequest, TokenOut, UserOut,
)
from app.services import auth as auth_service

router = APIRouter()

def _permission_to_http(exc: PermissionError) -> HTTPException:
    detail = str(exc)
    status_code = status.HTTP_403_FORBIDDEN if detail in {"Account disabled", "Admin account required"} else status.HTTP_401_UNAUTHORIZED
    return HTTPException(status_code=status_code, detail=detail)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.register(db, body.username, body.password, body.email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return user


@router.post("/login", response_model=TokenOut)
async def login(body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        payload = await auth_service.login(
            db, body.username, body.password,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except PermissionError as exc:
        raise _permission_to_http(exc)
    response.set_cookie("access_token", payload["access_token"], httponly=True, samesite="lax", path="/")
    response.set_cookie("refresh_token", payload["refresh_token"], httponly=True, samesite="lax", path="/api/auth")
    return TokenOut(**payload)


@router.post("/refresh", response_model=AccessTokenOut)
async def refresh_token(body: RefreshRequest, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        access = await auth_service.refresh(db, body.refresh_token)
    except PermissionError as exc:
        raise _permission_to_http(exc)
    response.set_cookie("access_token", access, httponly=True, samesite="lax", path="/")
    return AccessTokenOut(access_token=access, expires_in=auth_service.settings.jwt_expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, response: Response, db: AsyncSession = Depends(get_db)):
    await auth_service.logout(db, body.refresh_token)
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")
