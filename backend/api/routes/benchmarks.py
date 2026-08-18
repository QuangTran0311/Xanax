"""API Routes – Benchmark management CRUD"""
import asyncio
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from hub.database import (
    list_benchmarks, get_benchmark, create_benchmark, update_benchmark,
    delete_benchmark, get_benchmark_results,
)
from hub.events import EventType, event_bus

router = APIRouter()
_RUNNING_EDIT_MESSAGE = (
    "Bài đánh giá đang chạy; hãy chờ chạy xong rồi mới sửa để tránh trộn "
    "hai bộ đề trong cùng một kết quả"
)


class TestCase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prompt: str = ""
    criteria: str = ""

    @field_validator("prompt", mode="before")
    @classmethod
    def validate_prompt(cls, value):
        if not isinstance(value, str):
            raise ValueError("prompt của mỗi đề phải là chuỗi")
        return value

    @field_validator("criteria", mode="before")
    @classmethod
    def validate_criteria(cls, value):
        if not isinstance(value, str):
            raise ValueError("criteria của mỗi đề phải là chuỗi")
        return value


class BenchmarkCreate(BaseModel):
    name: str = Field(..., min_length=1)
    role_description: str = Field("")
    test_cases: list[TestCase] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)


class BenchmarkUpdate(BaseModel):
    name: str | None = None
    role_description: str | None = None
    test_cases: list[TestCase] | None = None
    models: list[str] | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Tên bài đánh giá không được để trống")
        return value.strip()

    @field_validator("role_description", mode="before")
    @classmethod
    def validate_role_description(cls, value):
        if not isinstance(value, str):
            raise ValueError("Mô tả vai trò phải là chuỗi")
        return value

    @field_validator("test_cases", mode="before")
    @classmethod
    def validate_test_cases_shape(cls, value):
        if not isinstance(value, list):
            raise ValueError("test_cases phải là một danh sách")
        for index, item in enumerate(value, start=1):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Đề số {index} phải có hai trường prompt và criteria"
                )
        return value

    @field_validator("test_cases")
    @classmethod
    def validate_test_cases_prompt(cls, value):
        if not any(test_case.prompt.strip() for test_case in value):
            raise ValueError("Danh sách đề phải có ít nhất một prompt không rỗng")
        return value

    @field_validator("models", mode="before")
    @classmethod
    def validate_models(cls, value):
        if not isinstance(value, list) or any(
            not isinstance(model, str) for model in value
        ):
            raise ValueError("models phải là danh sách chuỗi")
        return value


def _emit_data_changed():
    asyncio.create_task(event_bus.emit_simple(EventType.DATA_CHANGED, "benchmarks"))


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


@router.patch("/{benchmark_id}")
async def patch_benchmark(benchmark_id: int, body: BenchmarkUpdate):
    current = await get_benchmark(benchmark_id)
    if not current:
        raise HTTPException(404, "Không tìm thấy bài đánh giá")

    # Không cho đổi bộ đề giữa một lượt chạy: các model đã xong và chưa chạy sẽ
    # dùng hai cấu hình khác nhau, khiến cùng một kết quả chứa dữ liệu bị trộn.
    if current.get("status") == "running":
        raise HTTPException(409, _RUNNING_EDIT_MESSAGE)

    fields = body.model_fields_set
    kwargs = {}
    if "name" in fields:
        kwargs["name"] = body.name
    if "role_description" in fields:
        kwargs["role_description"] = body.role_description
    if "test_cases" in fields:
        kwargs["test_cases_json"] = json.dumps(
            [test_case.model_dump() for test_case in body.test_cases or []]
        )
    if "models" in fields:
        kwargs["models_json"] = json.dumps(body.models)

    if kwargs:
        ok = await update_benchmark(benchmark_id, **kwargs)
        if not ok:
            # update_benchmark có thêm điều kiện nguyên tử để khép cửa race với
            # WebSocket vừa bắt đầu chạy sau lần đọc `current` ở trên.
            latest = await get_benchmark(benchmark_id)
            if latest and latest.get("status") == "running":
                raise HTTPException(409, _RUNNING_EDIT_MESSAGE)
            raise HTTPException(404, "Không tìm thấy bài đánh giá")
        _emit_data_changed()

    updated = await get_benchmark(benchmark_id)
    if not updated:
        raise HTTPException(404, "Không tìm thấy bài đánh giá")
    return _parse(updated)


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
