"""API Routes – AI Agent configuration CRUD"""
import asyncio
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from hub.database import (
    list_agent_configs, get_agent_config, create_agent_config,
    update_agent_config, delete_agent_config,
)
from hub.events import EventType, event_bus

router = APIRouter()

MAX_MODELS_PER_AGENT = 5


def _emit_data_changed():
    asyncio.create_task(event_bus.emit_simple(EventType.DATA_CHANGED, "agent_configs"))


def _check_max_models(v: list[int] | None) -> list[int] | None:
    if v is not None and len(v) > MAX_MODELS_PER_AGENT:
        raise ValueError(f"Tối đa {MAX_MODELS_PER_AGENT} model cho mỗi nhân viên")
    return v


class AgentConfigCreate(BaseModel):
    name: str = Field(..., min_length=1)
    role: str = Field("Assistant")
    model: str = Field("")
    model_pool_ids: list[int] = Field(default_factory=list)
    system_prompt: str = Field("")
    avatar_color: str = Field("#9366ff")
    avatar_icon: str = Field("bot")
    skills: list[int] = Field(default_factory=list)
    department_id: int | None = None

    @field_validator("model_pool_ids")
    @classmethod
    def _validate_ids(cls, v):
        return _check_max_models(v)


class AgentConfigUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    model: str | None = None
    model_pool_ids: list[int] | None = None
    system_prompt: str | None = None
    avatar_color: str | None = None
    avatar_icon: str | None = None
    skills: list[int] | None = None
    enabled: int | None = None
    department_id: int | None = None

    @field_validator("model_pool_ids")
    @classmethod
    def _validate_ids(cls, v):
        return _check_max_models(v)


def _parse_agent(agent: dict) -> dict:
    agent["skills"] = json.loads(agent.get("skills_json", "[]"))
    try:
        agent["model_pool_ids"] = json.loads(agent.get("model_pool_ids_json") or "[]")
    except Exception:
        agent["model_pool_ids"] = []
    return agent


@router.get("/")
async def list_agents():
    configs = await list_agent_configs()
    return {"agents": [_parse_agent(c) for c in configs]}


@router.post("/", status_code=201)
async def create_agent(body: AgentConfigCreate):
    agent_id = await create_agent_config(
        name=body.name,
        role=body.role,
        model=body.model,
        model_pool_id=body.model_pool_ids[0] if body.model_pool_ids else None,
        model_pool_ids_json=json.dumps(body.model_pool_ids),
        system_prompt=body.system_prompt,
        avatar_color=body.avatar_color,
        avatar_icon=body.avatar_icon,
        skills_json=json.dumps(body.skills),
        department_id=body.department_id,
    )
    agent = _parse_agent(await get_agent_config(agent_id))
    from core.agent_soul import ensure_soul_file
    ensure_soul_file(agent)
    _emit_data_changed()
    return agent


@router.get("/{agent_id}")
async def get_agent(agent_id: int):
    agent = await get_agent_config(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return _parse_agent(agent)


@router.patch("/{agent_id}")
async def patch_agent(agent_id: int, body: AgentConfigUpdate):
    kwargs = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if "skills" in kwargs:
        kwargs["skills_json"] = json.dumps(kwargs.pop("skills"))
    if "model_pool_ids" in kwargs:
        ids = kwargs.pop("model_pool_ids") or []
        kwargs["model_pool_ids_json"] = json.dumps(ids)
        kwargs["model_pool_id"] = ids[0] if ids else None
    ok = await update_agent_config(agent_id, **kwargs)
    if not ok:
        raise HTTPException(404, "Agent not found")
    agent = _parse_agent(await get_agent_config(agent_id))
    _emit_data_changed()
    return agent


@router.delete("/{agent_id}", status_code=204)
async def remove_agent(agent_id: int):
    ok = await delete_agent_config(agent_id)
    if not ok:
        raise HTTPException(404, "Agent not found")
    _emit_data_changed()
