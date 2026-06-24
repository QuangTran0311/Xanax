from fastapi import APIRouter, Depends

from app.api.deps import require_role
from app.schemas.workspace import WorkspaceOut, WorkspaceUserOut

router = APIRouter()


@router.get("", response_model=WorkspaceOut)
@router.get("/", response_model=WorkspaceOut, include_in_schema=False)
async def workspace(payload: dict = Depends(require_role("admin", "owner"))):
    user = WorkspaceUserOut(
        id=payload["sub"],
        username=payload["username"],
        role=payload["role"],
    )
    return WorkspaceOut(user=user)
