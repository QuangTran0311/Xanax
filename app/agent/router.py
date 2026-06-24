from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.intelligence import ModelScore, ModelRegistry
from app.utils.logger import logger

DEFAULT_MODEL = "claude-sonnet-4-6"


async def pick_best_model(
    db: AsyncSession,
    task_type: str,
    modality: str = "text",
) -> str:
    """Chọn model có final_score cao nhất cho task_type + modality đã cho."""
    try:
        result = await db.execute(
            select(ModelScore)
            .join(ModelRegistry, ModelScore.model_id == ModelRegistry.model_id)
            .where(
                ModelScore.task_type == task_type,
                ModelRegistry.modality == modality,
                ModelRegistry.is_active.is_(True),
            )
            .order_by(ModelScore.final_score.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            return row.model_id
    except Exception as exc:
        logger.error(f"Model router error: {exc}")

    return DEFAULT_MODEL
