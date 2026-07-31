"""API Routes – Benchmark management CRUD"""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hub.database import (
    list_benchmarks, get_benchmark, create_benchmark, update_benchmark,
    delete_benchmark, get_benchmark_results,
)

router = APIRouter()


class TestCase(BaseModel):
    prompt: str
    criteria: str = ""


class BenchmarkCreate(BaseModel):
    name: str = Field(..., min_length=1)
    role_description: str = Field("")
    test_cases: list[TestCase] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)


def _parse(b: dict) -> dict:
    b["test_cases"] = json.loads(b.get("test_cases_json", "[]"))
    b["models"] = json.loads(b.get("models_json", "[]"))
    return b


@router.get("/")
async def list_all():
    benchmarks = await list_benchmarks()
    return {"benchmarks": [_parse(b) for b in benchmarks]}


@router.post("/", status_code=201)
async def create_new(body: BenchmarkCreate):
    bid = await create_benchmark(
        name=body.name,
        role_description=body.role_description,
        test_cases_json=json.dumps([tc.model_dump() for tc in body.test_cases]),
        models_json=json.dumps(body.models),
    )
    b = await get_benchmark(bid)
    return _parse(b)


@router.get("/{benchmark_id}")
async def get_one(benchmark_id: int):
    b = await get_benchmark(benchmark_id)
    if not b:
        raise HTTPException(404, "Benchmark not found")
    return _parse(b)


@router.delete("/{benchmark_id}", status_code=204)
async def remove(benchmark_id: int):
    ok = await delete_benchmark(benchmark_id)
    if not ok:
        raise HTTPException(404, "Benchmark not found")


@router.get("/{benchmark_id}/results")
async def get_results(benchmark_id: int):
    b = await get_benchmark(benchmark_id)
    if not b:
        raise HTTPException(404, "Benchmark not found")
    results = await get_benchmark_results(benchmark_id)
    for r in results:
        r["scores"] = json.loads(r.get("scores_json", "{}"))
        r["responses"] = json.loads(r.get("responses_json", "[]"))
    return {"results": results}
