"""API Routes – Agent management"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.orchestrator import AgentRunStatus, orchestrator

router = APIRouter()


class SpawnAgentRequest(BaseModel):
    task: str = Field(..., min_length=1, description="Task description for the agent")
    agent_name: str = Field("hermes", description="Name/identifier for the agent")
    metadata: dict = Field(default_factory=dict, description="Optional metadata")


class SpawnAgentResponse(BaseModel):
    record_id: str
    agent_name: str
    task: str
    status: str
    message: str


@router.post("/spawn", response_model=SpawnAgentResponse, summary="Spawn a new Hermes agent")
async def spawn_agent(body: SpawnAgentRequest):
    """Create and start a new Hermes agent for the given task."""
    record = await orchestrator.spawn_agent(
        task=body.task,
        agent_name=body.agent_name,
        metadata=body.metadata,
    )
    return SpawnAgentResponse(
        record_id=record.record_id,
        agent_name=record.agent_name,
        task=record.task,
        status=record.status.value,
        message=f"Agent '{record.agent_name}' spawned successfully",
    )


@router.get("/", summary="List all agents")
async def list_agents(
    status: AgentRunStatus | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
):
    """List all agent records, optionally filtered by status."""
    records = await orchestrator.list_agents(status=status)
    return {
        "total": len(records),
        "agents": [r.to_dict() for r in records[:limit]],
    }


@router.get("/stats", summary="Orchestrator statistics")
async def get_stats():
    """Get aggregate statistics for all agents."""
    return await orchestrator.get_stats()


@router.get("/{record_id}", summary="Get agent details")
async def get_agent(record_id: str):
    """Get details for a specific agent record."""
    record = await orchestrator.get_agent(record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Agent record '{record_id}' not found")
    return record.to_dict()


@router.delete("/{record_id}", summary="Cancel an agent")
async def cancel_agent(record_id: str):
    """Cancel a running agent."""
    success = await orchestrator.cancel_agent(record_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent '{record_id}' not found or not cancellable")
    return {"message": f"Agent '{record_id}' cancelled"}
