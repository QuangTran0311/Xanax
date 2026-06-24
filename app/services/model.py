from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.intelligence import ModelRegistry, ModelScore, ModelUsageLog
from app.utils.logger import logger


async def list_active_models(db: AsyncSession) -> list[ModelRegistry]:
    result = await db.execute(select(ModelRegistry).where(ModelRegistry.is_active.is_(True)))
    return list(result.scalars().all())


async def get_model_scores(db: AsyncSession, model_id: str) -> list[ModelScore]:
    result = await db.execute(select(ModelScore).where(ModelScore.model_id == model_id))
    return list(result.scalars().all())


async def log_model_usage(db: AsyncSession, data: dict) -> None:
    """Ghi log usage và cập nhật rolling score cho model."""
    try:
        log = ModelUsageLog(**data)
        db.add(log)
        await db.flush()
        await _update_model_score(db, data["model_id"], data["task_type"], data)
        await db.commit()
    except Exception as exc:
        logger.error(f"log_model_usage failed: {exc}")
        await db.rollback()


async def _update_model_score(db: AsyncSession, model_id: str, task_type: str, usage: dict) -> None:
    existing = await db.scalar(
        select(ModelScore).where(
            ModelScore.model_id == model_id,
            ModelScore.task_type == task_type,
        )
    )
    n = (existing.sample_count if existing else 0) + 1
    prev_lat = existing.avg_latency_ms if existing else 0.0
    prev_cost = existing.avg_cost_usd if existing else 0.0
    prev_sr = existing.success_rate if existing else 1.0

    avg_latency = (prev_lat * (n - 1) + (usage.get("latency_ms") or 0)) / n
    avg_cost = (prev_cost * (n - 1) + (usage.get("cost_usd") or 0.0)) / n
    success_rate = (prev_sr * (n - 1) + (1 if usage.get("success", True) else 0)) / n
    final_score = success_rate * 0.5 - avg_cost * 10 - avg_latency / 10_000

    stmt = (
        insert(ModelScore)
        .values(
            model_id=model_id,
            task_type=task_type,
            avg_latency_ms=avg_latency,
            avg_cost_usd=avg_cost,
            success_rate=success_rate,
            sample_count=n,
            final_score=final_score,
        )
        .on_conflict_do_update(
            constraint="model_scores_modelId_taskType_key",
            set_=dict(
                avg_latency_ms=avg_latency,
                avg_cost_usd=avg_cost,
                success_rate=success_rate,
                sample_count=n,
                final_score=final_score,
            ),
        )
    )
    await db.execute(stmt)
