"""REST API cho thí nghiệm ablation cơ chế tự cải thiện."""
from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from core.experiment_runner import calculate_experiment_summary, experiment_runner
from hub.database import (
    create_experiment,
    get_agent_config,
    get_benchmark,
    get_experiment,
    get_model_pool_entry,
    get_project,
    list_experiment_judgements,
    list_experiment_trials,
    list_experiments,
    list_model_pool,
)

router = APIRouter()


class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    agent_id: int = Field(..., gt=0)
    project_id: int = Field(..., gt=0)
    benchmark_id: int = Field(..., gt=0)
    measured_model_pool_id: int = Field(..., gt=0)
    judge_model_pool_id: int | None = Field(None, gt=0)
    repetitions: int = Field(3, ge=1, le=20)


def _loads(value: str, fallback):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def _shape_experiment(row: dict, *, include_snapshots: bool = False) -> dict:
    shaped = dict(row)
    shaped["warnings"] = _loads(shaped.pop("warnings_json", "[]"), [])
    config_raw = shaped.pop("config_snapshot_json", "{}")
    soul_raw = shaped.pop("soul_snapshot_json", "{}")
    if include_snapshots:
        shaped["config_snapshot"] = _loads(config_raw, {})
        shaped["soul_snapshot"] = _loads(soul_raw, {})
    return shaped


def _same_underlying_model(first: dict, second: dict) -> bool:
    return (first.get("model_id") or "").strip().casefold() == (
        second.get("model_id") or ""
    ).strip().casefold()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new(body: ExperimentCreate):
    agent = await get_agent_config(body.agent_id)
    project = await get_project(body.project_id)
    benchmark = await get_benchmark(body.benchmark_id)
    measured = await get_model_pool_entry(body.measured_model_pool_id)
    if not agent:
        raise HTTPException(404, "Không tìm thấy nhân viên")
    if not project:
        raise HTTPException(404, "Không tìm thấy dự án")
    if not benchmark:
        raise HTTPException(404, "Không tìm thấy bộ đề")
    test_cases = _loads(benchmark.get("test_cases_json", "[]"), [])
    if not any(isinstance(case, dict) and str(case.get("prompt", "")).strip()
               for case in test_cases):
        raise HTTPException(422, "Bộ đề chưa có câu hỏi hợp lệ")
    if not measured or not measured.get("enabled"):
        raise HTTPException(422, "Model bị đo không tồn tại hoặc đang tắt")

    enabled_models = await list_model_pool(enabled_only=True)
    judge: dict | None = None
    if body.judge_model_pool_id:
        judge = await get_model_pool_entry(body.judge_model_pool_id)
        if not judge or not judge.get("enabled"):
            raise HTTPException(422, "Model giám khảo không tồn tại hoặc đang tắt")
    else:
        # Khác model thật, không chỉ khác dòng pool/tài khoản.
        judge = next(
            (entry for entry in enabled_models if not _same_underlying_model(entry, measured)),
            None,
        )
        if judge is None:
            judge = measured

    warnings: list[dict] = []
    if _same_underlying_model(judge, measured):
        warnings.append({
            "code": "judge_same_as_measured",
            "message": "Giám khảo trùng model đang bị đo; kết quả có nguy cơ thiên lệch tự chấm.",
        })

    experiment_id = await create_experiment(
        name=body.name.strip(),
        agent_id=body.agent_id,
        project_id=body.project_id,
        benchmark_id=body.benchmark_id,
        measured_model_pool_id=body.measured_model_pool_id,
        judge_model_pool_id=judge["id"],
        repetitions=body.repetitions,
        warnings_json=json.dumps(warnings, ensure_ascii=False),
    )
    return _shape_experiment(await get_experiment(experiment_id), include_snapshots=True)


@router.get("/")
async def list_all():
    rows = await list_experiments()
    return {"experiments": [_shape_experiment(row) for row in rows]}


@router.get("/{experiment_id}")
async def get_one(experiment_id: int):
    experiment = await get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(404, "Không tìm thấy thí nghiệm")
    trials = await list_experiment_trials(experiment_id)
    judgements = await list_experiment_judgements(experiment_id)
    for judgement in judgements:
        judgement["item_map"] = _loads(judgement.pop("item_map_json", "{}"), {})
    return {
        "experiment": _shape_experiment(experiment, include_snapshots=True),
        "trials": trials,
        "judgements": judgements,
    }


@router.post("/{experiment_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_experiment(experiment_id: int):
    experiment = await get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(404, "Không tìm thấy thí nghiệm")
    if experiment.get("status") != "pending":
        raise HTTPException(409, f"Không thể chạy thí nghiệm ở trạng thái {experiment.get('status')}")
    if not await experiment_runner.start(experiment_id):
        raise HTTPException(409, "Thí nghiệm đã được một tiến trình khác khởi chạy")
    return {"experiment_id": experiment_id, "status": "starting"}


@router.post("/{experiment_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_experiment(experiment_id: int):
    experiment = await get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(404, "Không tìm thấy thí nghiệm")
    if not await experiment_runner.cancel(experiment_id):
        raise HTTPException(409, f"Không thể huỷ thí nghiệm ở trạng thái {experiment.get('status')}")
    return {"experiment_id": experiment_id, "status": "cancelling"}


@router.get("/{experiment_id}/summary")
async def get_summary(experiment_id: int):
    experiment = await get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(404, "Không tìm thấy thí nghiệm")
    trials = await list_experiment_trials(experiment_id)
    return {
        "experiment_id": experiment_id,
        "status": experiment["status"],
        **calculate_experiment_summary(trials),
    }


@router.get("/{experiment_id}/csv")
async def export_csv(experiment_id: int):
    experiment = await get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(404, "Không tìm thấy thí nghiệm")
    trials = await list_experiment_trials(experiment_id)
    output = io.StringIO(newline="")
    fields = [
        "experiment_id", "experiment_name", "experiment_status", "agent_id", "agent_name",
        "project_id", "project_name", "benchmark_id", "benchmark_name",
        "measured_model_pool_id", "measured_model_name", "judge_model_pool_id",
        "judge_model_name", "repetitions", "trial_id", "condition", "case_index",
        "repetition", "execution_order", "judge_order", "prompt", "criteria", "response",
        "score", "score_reason", "response_classification", "trial_status", "error_text", "elapsed_seconds",
        "tokens_input", "tokens_cache", "tokens_output", "started_at", "completed_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for trial in trials:
        writer.writerow({
            "experiment_id": experiment_id,
            "experiment_name": experiment["name"],
            "experiment_status": experiment["status"],
            "agent_id": experiment["agent_id"],
            "agent_name": experiment.get("agent_name", ""),
            "project_id": experiment.get("project_id", ""),
            "project_name": experiment.get("project_name", ""),
            "benchmark_id": experiment["benchmark_id"],
            "benchmark_name": experiment.get("benchmark_name", ""),
            "measured_model_pool_id": experiment["measured_model_pool_id"],
            "measured_model_name": experiment.get("measured_model_name", ""),
            "judge_model_pool_id": experiment["judge_model_pool_id"],
            "judge_model_name": experiment.get("judge_model_name", ""),
            "repetitions": experiment["repetitions"],
            "trial_id": trial["id"],
            "condition": trial["condition"],
            "case_index": trial["case_index"],
            "repetition": trial["repetition"],
            "execution_order": trial["execution_order"],
            "judge_order": trial.get("judge_order", ""),
            "prompt": trial["prompt"],
            "criteria": trial["criteria"],
            "response": trial["response"],
            "score": trial.get("score", ""),
            "score_reason": trial.get("score_reason", ""),
            "response_classification": trial.get("response_classification", "answered"),
            "trial_status": trial["status"],
            "error_text": trial.get("error_text", ""),
            "elapsed_seconds": trial.get("elapsed_seconds", 0),
            "tokens_input": trial.get("tokens_input", 0),
            "tokens_cache": trial.get("tokens_cache", 0),
            "tokens_output": trial.get("tokens_output", 0),
            "started_at": trial.get("started_at", ""),
            "completed_at": trial.get("completed_at", ""),
        })
    # BOM giúp Excel Windows nhận UTF-8 tiếng Việt đúng ngay khi mở trực tiếp.
    content = "\ufeff" + output.getvalue()
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="experiment_{experiment_id}.csv"'},
    )
