"""Shared FastAPI dependencies - inject into route handlers via Depends()."""
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.session import AsyncSessionLocal, get_db
from app.services.auth import verify_access_token
from sqlalchemy.ext.asyncio import AsyncSession

# Re-export get_db so routes only import from deps
__all__ = ["get_db", "require_auth", "require_role"]

_bearer = HTTPBearer(auto_error=False)


def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> dict:
    """Validate Bearer JWT and return the decoded payload dict."""
    token = credentials.credentials if credentials else request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        return verify_access_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def require_role(*roles: str):
    """Factory: returns a dependency that checks role membership."""
    def _check(payload: dict = Depends(require_auth)) -> dict:
        if payload.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return payload
    return _check
