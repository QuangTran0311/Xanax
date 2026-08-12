"""
Hub Event Bus – Pub/Sub messaging between agents and components
"""
import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine


class EventType(str, Enum):
    # Agent lifecycle
    AGENT_REGISTERED = "agent.registered"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"
    AGENT_STATUS_CHANGED = "agent.status_changed"

    # Task lifecycle
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # Hermes
    HERMES_THOUGHT = "hermes.thought"
    HERMES_ACTION = "hermes.action"
    HERMES_OBSERVATION = "hermes.observation"
    HERMES_PLAN_UPDATED = "hermes.plan_updated"

    # Data changes (agent, project, skill, work_item)
    DATA_CHANGED = "data.changed"

    # System
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_METRIC = "system.metric"


@dataclass
class Event:
    type: EventType
    data: Any = None
    source: str = "system"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "type": self.type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


Handler = Callable[[Event], Coroutine]


class EventBus:
    """Async pub/sub event bus for inter-component communication."""

    def __init__(self):
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._wildcard_subscribers: list[Handler] = []
        self._history: list[Event] = []
        self._max_history: int = 500
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: EventType | str, handler: Handler) -> None:
        """Subscribe to a specific event type."""
        key = event_type.value if isinstance(event_type, EventType) else event_type
        self._subscribers[key].append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        """Subscribe to ALL events (wildcard)."""
        self._wildcard_subscribers.append(handler)

    def unsubscribe(self, event_type: EventType | str, handler: Handler) -> None:
        key = event_type.value if isinstance(event_type, EventType) else event_type
        self._subscribers[key] = [h for h in self._subscribers[key] if h is not handler]

    async def emit(self, event: Event) -> None:
        """Emit an event to all subscribers."""
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)

        # Notify specific subscribers
        key = event.type.value
        handlers = self._subscribers.get(key, []) + self._wildcard_subscribers

        if handlers:
            await asyncio.gather(
                *[self._safe_call(h, event) for h in handlers],
                return_exceptions=True,
            )

    async def emit_simple(self, event_type: EventType, data: Any = None, source: str = "system") -> None:
        """Convenience method to emit without constructing Event manually."""
        await self.emit(Event(type=event_type, data=data, source=source))

    async def _safe_call(self, handler: Handler, event: Event) -> None:
        try:
            await handler(event)
        except Exception as e:
            # Avoid infinite recursion – don't emit error events here
            print(f"[EventBus] Handler error for {event.type}: {e}")

    def get_history(self, limit: int = 50) -> list[dict]:
        return [e.to_dict() for e in self._history[-limit:]]


# Global event bus singleton
event_bus = EventBus()
