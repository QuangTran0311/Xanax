"""
Xanax Hub Tools – Registered tools that give Hermes agents direct access
to Xanax Hub capabilities: spawning agents, checking status, scheduling tasks.
"""
from __future__ import annotations

import httpx
import logging
from typing import Any

from core.hermes.tool_registry import tool_registry

logger = logging.getLogger("xanax.tools.hub")


# ── Agent Management Tools ─────────────────────────────────────────────────

@tool_registry.register(
    name="spawn_agent",
    description="Spawn a new Hermes sub-agent to handle a task. Returns the agent record ID.",
    tags=["xanax", "orchestration", "multi-agent"]
)
async def spawn_agent(task: str, agent_name: str = "sub-agent") -> str:
    """Spawn a sub-agent to handle a task asynchronously."""
    try:
        from core.orchestrator import orchestrator
        record = await orchestrator.spawn_agent(task=task, agent_name=agent_name)
        return f"Agent spawned. ID: {record.record_id} | Name: {record.agent_name} | Status: {record.status.value}"
    except Exception as e:
        logger.exception("spawn_agent failed")
        return f"Error spawning agent: {e}"


@tool_registry.register(
    name="get_agent_status",
    description="Get the current status and result of a Hermes agent by its record ID.",
    tags=["xanax", "orchestration", "monitoring"]
)
async def get_agent_status(record_id: str) -> str:
    """Check status and result of a specific agent run."""
    try:
        from core.orchestrator import orchestrator
        record = await orchestrator.get_agent(record_id)
        if not record:
            return f"No agent found with ID: {record_id}"

        result = f"Agent '{record.agent_name}' [{record.status.value}]"
        if record.context and record.context.final_answer:
            result += f"\nAnswer: {record.context.final_answer[:500]}"
        if record.error:
            result += f"\nError: {record.error}"
        if record.finished_at:
            elapsed = (record.finished_at - record.created_at).total_seconds()
            result += f"\nCompleted in {elapsed:.1f}s"
        return result
    except Exception as e:
        return f"Error checking agent: {e}"


@tool_registry.register(
    name="list_agents",
    description="List all Hermes agents managed by the Xanax orchestrator, with their status.",
    tags=["xanax", "orchestration", "monitoring"]
)
async def list_agents(status_filter: str = "") -> str:
    """List all agents, optionally filtered by status (running/completed/failed/cancelled/pending)."""
    try:
        from core.orchestrator import orchestrator, AgentRunStatus
        status_map = {
            "running": AgentRunStatus.RUNNING,
            "completed": AgentRunStatus.COMPLETED,
            "failed": AgentRunStatus.FAILED,
            "cancelled": AgentRunStatus.CANCELLED,
            "pending": AgentRunStatus.PENDING,
        }
        filter_status = status_map.get(status_filter.lower()) if status_filter else None
        records = await orchestrator.list_agents(status=filter_status)

        if not records:
            return "No agents found."

        lines = [f"Found {len(records)} agent(s):\n"]
        for r in records[:20]:  # Limit to 20
            line = f"  [{r.status.value:10}] {r.agent_name:20} | {r.record_id[:8]}... | {r.task[:60]}"
            lines.append(line)
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing agents: {e}"


@tool_registry.register(
    name="cancel_agent",
    description="Cancel a running Hermes agent by its record ID.",
    tags=["xanax", "orchestration"]
)
async def cancel_agent(record_id: str) -> str:
    """Cancel a running agent."""
    try:
        from core.orchestrator import orchestrator
        success = await orchestrator.cancel_agent(record_id)
        return f"Agent {record_id[:8]}... {'cancelled successfully.' if success else 'not found or already stopped.'}"
    except Exception as e:
        return f"Error cancelling agent: {e}"


@tool_registry.register(
    name="hub_stats",
    description="Get statistics about the Xanax Hub: agent counts, server status, and health.",
    tags=["xanax", "monitoring", "health"]
)
async def hub_stats() -> str:
    """Get hub statistics and health information."""
    try:
        from core.orchestrator import orchestrator
        stats = await orchestrator.get_stats()
        return (
            f"Xanax Hub Stats:\n"
            f"  Total agents: {stats['total']}\n"
            f"  Running:       {stats['running']}\n"
            f"  Completed:     {stats['completed']}\n"
            f"  Failed:        {stats['failed']}\n"
            f"  Cancelled:     {stats['cancelled']}\n"
            f"  Pending:       {stats['pending']}"
        )
    except Exception as e:
        return f"Error fetching hub stats: {e}"


# ── Scheduler Tools ────────────────────────────────────────────────────────

@tool_registry.register(
    name="list_scheduled_tasks",
    description="List all scheduled tasks in the Xanax task scheduler.",
    tags=["xanax", "scheduler", "monitoring"]
)
async def list_scheduled_tasks() -> str:
    """List all scheduled/recurring tasks."""
    try:
        from core.scheduler import task_scheduler
        tasks = task_scheduler.list_jobs()
        if not tasks:
            return "No scheduled tasks."
        lines = [f"Scheduled tasks ({len(tasks)}):\n"]
        for job in tasks:
            lines.append(f"  {job.get('id', '?'):30} | next: {job.get('next_run', 'N/A')}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing tasks: {e}"


# ── HTTP Tools ─────────────────────────────────────────────────────────────

@tool_registry.register(
    name="http_get",
    description="Perform an HTTP GET request to a URL and return the response body.",
    tags=["http", "web", "api"]
)
async def http_get(url: str, timeout: int = 30) -> str:
    """Make an HTTP GET request."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            text = response.text
            return text[:2000] if len(text) > 2000 else text
    except httpx.HTTPStatusError as e:
        return f"HTTP {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"HTTP GET failed: {e}"


@tool_registry.register(
    name="http_post",
    description="Perform an HTTP POST request with a JSON body to a URL.",
    tags=["http", "web", "api"]
)
async def http_post(url: str, body: str = "{}") -> str:
    """Make an HTTP POST request with a JSON body (as a string)."""
    import json
    try:
        payload = json.loads(body)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.text[:2000]
    except json.JSONDecodeError:
        return f"Invalid JSON body: {body}"
    except httpx.HTTPStatusError as e:
        return f"HTTP {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"HTTP POST failed: {e}"
