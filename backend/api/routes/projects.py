"""API Routes – Projects and Work Items (kanban) CRUD + smart agent-task matching"""
import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from hub.events import EventType, event_bus
from hub.database import (
    list_projects, get_project, create_project, update_project, delete_project,
    list_work_items, get_work_item, create_work_item, update_work_item, delete_work_item,
    get_all_agents_with_skills,
    create_task_alert, resolve_task_alert, list_task_alerts, delete_task_alert_for_item,
    get_open_alert_count,
)
from core.matcher import match_agent_for_task, match_result_to_dict
from core.project_storage import PROJECTS_DATA_DIR

router = APIRouter()


def _emit_data_changed():
    asyncio.create_task(event_bus.emit_simple(EventType.DATA_CHANGED, "projects"))


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field("")


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class WorkItemCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field("")
    status: str = Field("backlog")
    priority: str = Field("medium")
    assigned_agent_id: int | None = None


class WorkItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_agent_id: int | None = None


class MatchPreview(BaseModel):
    title: str = Field("")
    description: str = Field("")


# ── Projects ──────────────────────────────────────────────────────────────────

@router.get("/")
async def list_all_projects():
    return {"projects": await list_projects()}


@router.post("/", status_code=201)
async def create_new_project(body: ProjectCreate):
    project_id = await create_project(body.name, body.description)
    _emit_data_changed()
    return await get_project(project_id)


@router.get("/{project_id}")
async def get_one_project(project_id: int):
    project = await get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.patch("/{project_id}")
async def patch_project(project_id: int, body: ProjectUpdate):
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    ok = await update_project(project_id, **kwargs)
    if not ok:
        raise HTTPException(404, "Project not found")
    _emit_data_changed()
    return await get_project(project_id)


@router.delete("/{project_id}", status_code=204)
async def remove_project(project_id: int):
    ok = await delete_project(project_id)
    if not ok:
        raise HTTPException(404, "Project not found")
    _emit_data_changed()


# ── Archive (kết quả quy trình đã lưu ra đĩa theo dự án) ──────────────────────

def _project_archive_dir(project: dict) -> Path:
    return PROJECTS_DATA_DIR / (project.get("slug") or "")


@router.get("/{project_id}/archive")
async def list_project_archive(project_id: int):
    """Liệt kê các lần chạy đã được lưu trữ ra đĩa cho dự án này (đọc run_info.json)."""
    project = await get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    base = _project_archive_dir(project)
    runs = []
    if base.is_dir():
        for run_info_path in base.glob("*/*/run_info.json"):
            try:
                info = json.loads(run_info_path.read_text(encoding="utf-8"))
                info["archive_path"] = str(run_info_path.parent.relative_to(base))
                runs.append(info)
            except Exception:
                continue
    runs.sort(key=lambda r: r.get("archive_path", ""), reverse=True)
    return {"runs": runs}


@router.get("/{project_id}/archive-file")
async def get_project_archive_file(project_id: int, path: str):
    """Tải 1 file cụ thể trong archive (đường dẫn tương đối trả về từ /archive)."""
    project = await get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    base = _project_archive_dir(project).resolve()
    target = (base / path).resolve()
    if base not in target.parents or not target.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(target)


# ── Work Items ────────────────────────────────────────────────────────────────

@router.get("/items/alerts")
async def get_alerts():
    alerts = await list_task_alerts("open")
    count = await get_open_alert_count()
    return {"alerts": alerts, "count": count}


@router.post("/items/match")
async def preview_match(body: MatchPreview):
    """Return match suggestions for a title+description without saving anything."""
    agents = await get_all_agents_with_skills()
    result = match_agent_for_task(body.title, body.description, agents)
    return match_result_to_dict(result)


@router.get("/{project_id}/items")
async def list_items(project_id: int):
    project = await get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return {"items": await list_work_items(project_id)}


@router.post("/{project_id}/items", status_code=201)
async def create_item(project_id: int, body: WorkItemCreate):
    project = await get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    item_id = await create_work_item(
        project_id=project_id,
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        assigned_agent_id=body.assigned_agent_id,
    )

    # Run matcher (only when no agent is manually pre-assigned)
    match_dict = None
    if not body.assigned_agent_id:
        agents = await get_all_agents_with_skills()
        result = match_agent_for_task(body.title, body.description, agents)
        match_dict = match_result_to_dict(result)
        best = result.best
        await update_work_item(
            item_id,
            match_score=best.score if best else 0.0,
            match_reason=best.reason if best else "",
        )
        if not result.has_match:
            suggestions = json.dumps([c for c in match_dict["suggestions"]])
            await create_task_alert(
                item_id, project_id, body.title,
                reason="no_matching_agent",
                suggestions_json=suggestions,
            )

    items = await list_work_items(project_id)
    item = next((i for i in items if i["id"] == item_id), {})
    _emit_data_changed()
    return {"item": item, "match": match_dict}


@router.patch("/items/{item_id}")
async def patch_item(item_id: int, body: WorkItemUpdate):
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    # allow explicit null agent assignment
    if body.assigned_agent_id is None and "assigned_agent_id" in body.model_fields_set:
        kwargs["assigned_agent_id"] = None

    ok = await update_work_item(item_id, **kwargs)
    if not ok:
        raise HTTPException(404, "Work item not found")

    # Resolve alert when agent is explicitly assigned
    if kwargs.get("assigned_agent_id"):
        await resolve_task_alert(item_id)

    # Re-run matcher when content fields change
    match_dict = None
    content_changed = bool({"title", "description"} & set(kwargs))
    if content_changed:
        current = await get_work_item(item_id)
        if current:
            agents = await get_all_agents_with_skills()
            result = match_agent_for_task(
                current["title"], current["description"], agents
            )
            match_dict = match_result_to_dict(result)
            best = result.best
            await update_work_item(
                item_id,
                match_score=best.score if best else 0.0,
                match_reason=best.reason if best else "",
            )
            assigned = current.get("assigned_agent_id")
            if not result.has_match and not assigned:
                suggestions = json.dumps(match_dict["suggestions"])
                await create_task_alert(
                    item_id, current["project_id"], current["title"],
                    reason="no_matching_agent",
                    suggestions_json=suggestions,
                )
            elif result.has_match or assigned:
                await resolve_task_alert(item_id)

    _emit_data_changed()
    return {"ok": True, "match": match_dict}


@router.delete("/items/{item_id}", status_code=204)
async def remove_item(item_id: int):
    await delete_task_alert_for_item(item_id)
    ok = await delete_work_item(item_id)
    if not ok:
        raise HTTPException(404, "Work item not found")
    _emit_data_changed()
