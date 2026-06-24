from datetime import datetime

from pydantic import BaseModel


class ModelOut(BaseModel):
    model_config = {"from_attributes": True}

    model_id: str
    provider: str
    modality: str
    context_window: int | None
    supports_stream: bool
    cost_per_1k_input: float | None
    cost_per_1k_output: float | None
    is_active: bool


class ModelScoreOut(BaseModel):
    model_config = {"from_attributes": True}

    model_id: str
    task_type: str
    avg_latency_ms: float
    avg_cost_usd: float
    success_rate: float
    quality_score: float
    sample_count: int
    final_score: float
    updated_at: datetime


class LogUsageRequest(BaseModel):
    session_id: str
    model_id: str
    task_type: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost_usd: float | None = None
    success: bool = True
    error_msg: str | None = None
