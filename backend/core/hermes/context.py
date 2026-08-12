"""
Hermes Agent Context – Shared state & metadata for an agent run
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class Thought:
    content: str
    iteration: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "iteration": self.iteration,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Action:
    tool_name: str
    tool_args: dict
    result: Any = None
    error: str | None = None
    iteration: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "result": self.result,
            "error": self.error,
            "iteration": self.iteration,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AgentContext:
    """Holds all runtime state for a single agent execution."""

    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = "hermes"
    task: str = ""
    status: AgentStatus = AgentStatus.IDLE

    # Execution trace
    thoughts: list[Thought] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)

    # Results
    final_answer: str | None = None
    error: str | None = None

    # Metadata
    iteration: int = 0
    max_iterations: int = 10
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Extra key-value store
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_thought(self, content: str) -> Thought:
        thought = Thought(content=content, iteration=self.iteration)
        self.thoughts.append(thought)
        self._touch()
        return thought

    def add_action(self, tool_name: str, tool_args: dict) -> Action:
        action = Action(tool_name=tool_name, tool_args=tool_args, iteration=self.iteration)
        self.actions.append(action)
        self._touch()
        return action

    def set_status(self, status: AgentStatus) -> None:
        self.status = status
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "task": self.task,
            "status": self.status.value,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "plan": self.plan,
            "thoughts": [t.to_dict() for t in self.thoughts],
            "actions": [a.to_dict() for a in self.actions],
            "final_answer": self.final_answer,
            "error": self.error,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @property
    def is_done(self) -> bool:
        return self.status in (AgentStatus.DONE, AgentStatus.ERROR, AgentStatus.STOPPED)

    @property
    def has_exceeded_limit(self) -> bool:
        return self.iteration >= self.max_iterations
