from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.model import LogUsageRequest, ModelOut, ModelScoreOut
from app.services import model as model_service

router = APIRouter()


@router.get("/", response_model=list[ModelOut])
async def list_models(db: AsyncSession = Depends(get_db)):
    return await model_service.list_active_models(db)


@router.get("/{model_id}/scores", response_model=list[ModelScoreOut])
async def get_scores(model_id: str, db: AsyncSession = Depends(get_db)):
    return await model_service.get_model_scores(db, model_id)


@router.post("/usage", status_code=201)
async def log_usage(body: LogUsageRequest, db: AsyncSession = Depends(get_db)):
    await model_service.log_model_usage(db, body.model_dump(exclude_none=True))
    return {"logged": True}
