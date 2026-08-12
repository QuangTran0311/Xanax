"""API Routes – Departments (phòng ban) CRUD. Nhóm nhân viên AI theo phòng ban,
chuẩn bị cho tính năng họp theo phòng ban."""
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hub.database import (
    list_departments, get_department, create_department, update_department, delete_department,
)
from hub.events import EventType, event_bus

router = APIRouter()


def _emit_data_changed():
    asyncio.create_task(event_bus.emit_simple(EventType.DATA_CHANGED, "departments"))


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field("")
    color: str = Field("#9366ff")
    head_agent_id: int | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    head_agent_id: int | None = None


@router.get("/")
async def list_all_departments():
    return {"departments": await list_departments()}


@router.post("/", status_code=201)
async def create_new_department(body: DepartmentCreate):
    department_id = await create_department(body.name, body.description, body.color, body.head_agent_id)
    _emit_data_changed()
    return await get_department(department_id)


@router.get("/{department_id}")
async def get_one_department(department_id: int):
    department = await get_department(department_id)
    if not department:
        raise HTTPException(404, "Department not found")
    return department


@router.patch("/{department_id}")
async def patch_department(department_id: int, body: DepartmentUpdate):
    kwargs = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    ok = await update_department(department_id, **kwargs)
    if not ok:
        raise HTTPException(404, "Department not found")
    _emit_data_changed()
    return await get_department(department_id)


@router.delete("/{department_id}", status_code=204)
async def remove_department(department_id: int):
    ok = await delete_department(department_id)
    if not ok:
        raise HTTPException(404, "Department not found")
    _emit_data_changed()
