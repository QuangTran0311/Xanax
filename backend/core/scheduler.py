"""
Task Scheduler – Async task queue + APScheduler for cron/delayed jobs
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from hub.events import EventType, event_bus

logger = logging.getLogger("xanax.scheduler")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueuedTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "unnamed"
    payload: dict = field(default_factory=dict)
    handler: Callable | None = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    priority: int = 5  # 1 (highest) → 10 (lowest)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "payload": self.payload,
            "status": self.status.value,
            "priority": self.priority,
            "result": str(self.result)[:200] if self.result else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


class TaskScheduler:
    """
    Combines:
      1. An asyncio Queue for immediate task execution
      2. APScheduler for cron/interval/one-shot scheduled jobs
    """

    def __init__(self, max_queue_size: int = 1000, worker_count: int = 4):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._tasks: dict[str, QueuedTask] = {}
        self._workers: list[asyncio.Task] = []
        self._worker_count = worker_count
        self._scheduler = AsyncIOScheduler()
        self._running = False
        self._lock = asyncio.Lock()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._running = True
        self._scheduler.start()

        # Spin up worker coroutines
        for i in range(self._worker_count):
            worker = asyncio.create_task(self._worker_loop(i), name=f"task-worker-{i}")
            self._workers.append(worker)

        logger.info("TaskScheduler started with %d workers", self._worker_count)

    async def stop(self) -> None:
        self._running = False
        self._scheduler.shutdown(wait=False)

        for worker in self._workers:
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

        logger.info("TaskScheduler stopped")

    # ── Immediate queue ────────────────────────────────────────────────────

    async def enqueue(
        self,
        name: str,
        handler: Callable[..., Coroutine],
        payload: dict | None = None,
        priority: int = 5,
    ) -> QueuedTask:
        """Add a task to the immediate execution queue."""
        task = QueuedTask(name=name, payload=payload or {}, handler=handler, priority=priority)

        async with self._lock:
            self._tasks[task.task_id] = task

        # PriorityQueue uses (priority, item) tuples
        await self._queue.put((priority, task.task_id))

        await event_bus.emit_simple(EventType.TASK_CREATED, data=task.to_dict())
        logger.debug("Enqueued task '%s' [id=%s]", name, task.task_id[:8])
        return task

    async def get_task(self, task_id: str) -> QueuedTask | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def list_tasks(self, status: TaskStatus | None = None) -> list[QueuedTask]:
        async with self._lock:
            tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    async def cancel_task(self, task_id: str) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False
        task.status = TaskStatus.CANCELLED
        task.finished_at = datetime.now(timezone.utc)
        await event_bus.emit_simple(EventType.TASK_CANCELLED, data=task.to_dict())
        return True

    # ── Scheduled jobs (APScheduler) ───────────────────────────────────────

    def schedule_cron(
        self,
        job_id: str,
        handler: Callable,
        cron_expr: str,
        **kwargs,
    ) -> str:
        """Schedule a recurring job using cron expression (e.g. '*/5 * * * *')."""
        parts = cron_expr.split()
        trigger = CronTrigger(
            minute=parts[0] if len(parts) > 0 else "*",
            hour=parts[1] if len(parts) > 1 else "*",
            day=parts[2] if len(parts) > 2 else "*",
            month=parts[3] if len(parts) > 3 else "*",
            day_of_week=parts[4] if len(parts) > 4 else "*",
        )
        self._scheduler.add_job(handler, trigger, id=job_id, replace_existing=True, **kwargs)
        logger.info("Scheduled cron job '%s': %s", job_id, cron_expr)
        return job_id

    def schedule_interval(
        self,
        job_id: str,
        handler: Callable,
        seconds: int = 60,
        **kwargs,
    ) -> str:
        """Schedule a recurring job at fixed intervals."""
        trigger = IntervalTrigger(seconds=seconds)
        self._scheduler.add_job(handler, trigger, id=job_id, replace_existing=True, **kwargs)
        logger.info("Scheduled interval job '%s': every %ds", job_id, seconds)
        return job_id

    def schedule_once(
        self,
        job_id: str,
        handler: Callable,
        run_at: datetime,
        **kwargs,
    ) -> str:
        """Schedule a one-shot job at a specific datetime."""
        trigger = DateTrigger(run_date=run_at)
        self._scheduler.add_job(handler, trigger, id=job_id, replace_existing=True, **kwargs)
        logger.info("Scheduled one-shot job '%s' at %s", job_id, run_at.isoformat())
        return job_id

    def remove_job(self, job_id: str) -> bool:
        try:
            self._scheduler.remove_job(job_id)
            return True
        except Exception:
            return False

    def list_jobs(self) -> list[dict]:
        return [
            {
                "job_id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in self._scheduler.get_jobs()
        ]

    async def get_queue_stats(self) -> dict:
        tasks = await self.list_tasks()
        return {
            "queue_size": self._queue.qsize(),
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            "running": sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
            "done": sum(1 for t in tasks if t.status == TaskStatus.DONE),
            "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            "cancelled": sum(1 for t in tasks if t.status == TaskStatus.CANCELLED),
            "scheduled_jobs": len(self.list_jobs()),
        }

    # ── Worker loop ────────────────────────────────────────────────────────

    async def _worker_loop(self, worker_id: int) -> None:
        logger.debug("Worker %d started", worker_id)
        while self._running:
            try:
                priority, task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            async with self._lock:
                task = self._tasks.get(task_id)

            if not task or task.status == TaskStatus.CANCELLED:
                self._queue.task_done()
                continue

            await self._execute_task(task)
            self._queue.task_done()

        logger.debug("Worker %d stopped", worker_id)

    async def _execute_task(self, task: QueuedTask) -> None:
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        await event_bus.emit_simple(EventType.TASK_STARTED, data=task.to_dict())

        try:
            if asyncio.iscoroutinefunction(task.handler):
                task.result = await task.handler(**task.payload)
            else:
                task.result = await asyncio.to_thread(task.handler, **task.payload)
            task.status = TaskStatus.DONE
            await event_bus.emit_simple(EventType.TASK_COMPLETED, data=task.to_dict())
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.exception("Task '%s' failed", task.name)
            await event_bus.emit_simple(EventType.TASK_FAILED, data=task.to_dict())
        finally:
            task.finished_at = datetime.now(timezone.utc)


# Global scheduler singleton
task_scheduler = TaskScheduler()
