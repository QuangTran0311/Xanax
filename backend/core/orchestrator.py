"""
Multi-Agent Orchestrator – Spawn, manage, and coordinate Hermes sub-agents
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.hermes.agent import HermesAgent
from core.hermes.context import AgentContext, AgentStatus
from hub.events import EventType, event_bus

logger = logging.getLogger("xanax.orchestrator")


class AgentRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentRecord:
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = "unnamed"
    task: str = ""
    status: AgentRunStatus = AgentRunStatus.PENDING
    agent: HermesAgent | None = None
    context: AgentContext | None = None
    asyncio_task: asyncio.Task | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "agent_name": self.agent_name,
            "task": self.task,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "context": self.context.to_dict() if self.context else None,
        }


class AgentOrchestrator:
    """
    Central orchestrator that manages the lifecycle of all Hermes agents.

    Responsibilities:
      - Create and track agent instances
      - Run agents as async tasks
      - Route events from agents to the event bus
      - Cancel / stop agents on demand
    """

    def __init__(self):
        self._records: dict[str, AgentRecord] = {}
        self._lock = asyncio.Lock()
        self._started = False

    async def start(self) -> None:
        self._started = True
        logger.info("AgentOrchestrator started")

    async def stop(self) -> None:
        """Cancel all running agents."""
        self._started = False
        async with self._lock:
            running = [r for r in self._records.values() if r.status == AgentRunStatus.RUNNING]
        for record in running:
            await self.cancel_agent(record.record_id)
        logger.info("AgentOrchestrator stopped")

    @property
    def started(self) -> bool:
        return self._started

    # ── Agent lifecycle ────────────────────────────────────────────────────

    async def spawn_agent(
        self,
        task: str,
        agent_name: str = "hermes",
        metadata: dict | None = None,
    ) -> AgentRecord:
        """
        Create a new HermesAgent and start it running in the background.
        Returns the AgentRecord immediately (non-blocking).
        """
        agent = HermesAgent(name=agent_name)
        record = AgentRecord(agent_name=agent_name, task=task, agent=agent)

        # Wire agent events → hub event bus
        async def on_agent_event(event_type: str, data: Any):
            await event_bus.emit_simple(
                EventType.HERMES_ACTION if event_type == "action" else
                EventType.HERMES_THOUGHT if event_type == "thought" else
                EventType.HERMES_OBSERVATION,
                data={"agent_id": record.record_id, "event": event_type, "data": data},
                source=record.record_id,
            )

        agent.on_event(on_agent_event)

        async with self._lock:
            self._records[record.record_id] = record

        # Start agent as background async task
        asyncio_task = asyncio.create_task(
            self._run_agent(record),
            name=f"agent-{record.record_id[:8]}",
        )
        record.asyncio_task = asyncio_task

        await event_bus.emit_simple(
            EventType.AGENT_REGISTERED,
            data=record.to_dict(),
            source="orchestrator",
        )
        logger.info("Spawned agent '%s' for task: %s", agent_name, task[:80])
        return record

    async def cancel_agent(self, record_id: str) -> bool:
        """Cancel a running agent by record ID."""
        async with self._lock:
            record = self._records.get(record_id)
        if not record:
            return False
        if record.asyncio_task and not record.asyncio_task.done():
            record.asyncio_task.cancel()
            try:
                await record.asyncio_task
            except asyncio.CancelledError:
                pass
        record.status = AgentRunStatus.CANCELLED
        record.finished_at = datetime.now(timezone.utc)
        await event_bus.emit_simple(EventType.AGENT_STOPPED, data={"record_id": record_id})
        return True

    async def get_agent(self, record_id: str) -> AgentRecord | None:
        async with self._lock:
            return self._records.get(record_id)

    async def list_agents(self, status: AgentRunStatus | None = None) -> list[AgentRecord]:
        async with self._lock:
            records = list(self._records.values())
        if status:
            records = [r for r in records if r.status == status]
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    async def get_stats(self) -> dict:
        records = await self.list_agents()
        return {
            "total": len(records),
            "pending": sum(1 for r in records if r.status == AgentRunStatus.PENDING),
            "running": sum(1 for r in records if r.status == AgentRunStatus.RUNNING),
            "completed": sum(1 for r in records if r.status == AgentRunStatus.COMPLETED),
            "failed": sum(1 for r in records if r.status == AgentRunStatus.FAILED),
            "cancelled": sum(1 for r in records if r.status == AgentRunStatus.CANCELLED),
        }

    # ── Internal ───────────────────────────────────────────────────────────

    async def _run_agent(self, record: AgentRecord) -> None:
        record.status = AgentRunStatus.RUNNING
        await event_bus.emit_simple(EventType.AGENT_STARTED, data=record.to_dict())

        try:
            context = await record.agent.run(record.task)
            record.context = context
            record.status = (
                AgentRunStatus.COMPLETED
                if context.status == AgentStatus.DONE
                else AgentRunStatus.FAILED
            )
            record.error = context.error
        except asyncio.CancelledError:
            record.status = AgentRunStatus.CANCELLED
        except Exception as e:
            record.status = AgentRunStatus.FAILED
            record.error = str(e)
            logger.exception("Agent '%s' crashed", record.agent_name)
            await event_bus.emit_simple(EventType.AGENT_ERROR, data={"record_id": record.record_id, "error": str(e)})
        finally:
            record.finished_at = datetime.now(timezone.utc)
            await event_bus.emit_simple(EventType.AGENT_STOPPED, data=record.to_dict())


# Global orchestrator singleton
orchestrator = AgentOrchestrator()
