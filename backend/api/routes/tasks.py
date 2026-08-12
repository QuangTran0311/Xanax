"""API Routes – Task queue management"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.scheduler import TaskStatus, task_scheduler

router = APIRouter()


class EnqueueTaskRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Task name")
    payload: dict = Field(default_factory=dict, description="Task payload / arguments")
    priority: int = Field(5, ge=1, le=10, description="Priority 1=highest, 10=lowest")


@router.post("/enqueue", summary="Enqueue a task for execution")
async def enqueue_task(body: EnqueueTaskRequest):
    """Add a task to the execution queue."""
    # For API-driven tasks, use a simple echo handler
    async def api_task(**kwargs):
        return {"executed": True, "payload": kwargs}

    task = await task_scheduler.enqueue(
        name=body.name,
        handler=api_task,
        payload=body.payload,
        priority=body.priority,
    )
    return task.to_dict()


@router.get("/", summary="List tasks")
async def list_tasks(
    status: TaskStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List all queued and completed tasks."""
    tasks = await task_scheduler.list_tasks(status=status)
    return {
        "total": len(tasks),
        "tasks": [t.to_dict() for t in tasks[:limit]],
    }


@router.get("/stats", summary="Task queue statistics")
async def queue_stats():
    """Get task queue statistics."""
    return await task_scheduler.get_queue_stats()


@router.get("/jobs", summary="List scheduled jobs")
async def list_jobs():
    """List all APScheduler cron/interval jobs."""
    return {"jobs": task_scheduler.list_jobs()}


@router.get("/{task_id}", summary="Get task details")
async def get_task(task_id: str):
    """Get details for a specific task."""
    task = await task_scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task.to_dict()


@router.delete("/{task_id}", summary="Cancel a pending task")
async def cancel_task(task_id: str):
    """Cancel a pending task."""
    success = await task_scheduler.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found or not cancellable")
    return {"message": f"Task '{task_id}' cancelled"}
