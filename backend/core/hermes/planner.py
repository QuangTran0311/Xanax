"""
Hermes Task Planner – Decomposes goals into executable steps
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    index: int
    description: str
    tool_hint: str | None = None       # Suggested tool to use
    depends_on: list[int] = field(default_factory=list)  # Step indices
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: str | None = None

    def mark_done(self, result: Any = None) -> None:
        self.status = StepStatus.DONE
        self.result = result

    def mark_failed(self, error: str) -> None:
        self.status = StepStatus.FAILED
        self.error = error

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "description": self.description,
            "tool_hint": self.tool_hint,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "result": str(self.result)[:200] if self.result else None,
            "error": self.error,
        }


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep] = field(default_factory=list)

    @property
    def current_step(self) -> PlanStep | None:
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                # Check all dependencies are done
                deps_done = all(
                    self.steps[i].status == StepStatus.DONE
                    for i in step.depends_on
                    if i < len(self.steps)
                )
                if deps_done:
                    return step
        return None

    @property
    def is_complete(self) -> bool:
        return all(s.status in (StepStatus.DONE, StepStatus.SKIPPED) for s in self.steps)

    @property
    def has_failed(self) -> bool:
        return any(s.status == StepStatus.FAILED for s in self.steps)

    @property
    def progress(self) -> float:
        if not self.steps:
            return 0.0
        done = sum(1 for s in self.steps if s.status in (StepStatus.DONE, StepStatus.SKIPPED))
        return done / len(self.steps)

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "progress": round(self.progress * 100, 1),
            "is_complete": self.is_complete,
            "has_failed": self.has_failed,
            "steps": [s.to_dict() for s in self.steps],
        }


class HermesPlanner:
    """
    Rule-based task planner for Hermes Agent.

    When an LLM backend is available, it delegates planning to the model.
    Without an LLM, it uses keyword-based heuristics to generate a plan.
    """

    TOOL_KEYWORDS = {
        "web_search": ["search", "find", "look up", "google", "research", "query"],
        "read_file": ["read", "open", "load", "view file", "check file"],
        "write_file": ["write", "save", "create file", "store"],
        "run_code": ["run", "execute", "code", "script", "compute", "calculate"],
        "list_files": ["list", "directory", "folder", "files in"],
        "http_get": ["fetch", "http", "request", "url", "api call"],
    }

    async def create_plan(self, goal: str, available_tools: list[str]) -> Plan:
        """Generate a Plan from a goal string."""
        plan = Plan(goal=goal)

        # Try rule-based decomposition
        steps = self._rule_based_decompose(goal, available_tools)

        for i, (desc, tool_hint) in enumerate(steps):
            plan.steps.append(
                PlanStep(index=i, description=desc, tool_hint=tool_hint)
            )

        return plan

    def _rule_based_decompose(
        self, goal: str, available_tools: list[str]
    ) -> list[tuple[str, str | None]]:
        """
        Decompose a goal into steps using heuristics.
        Returns list of (description, tool_hint) tuples.
        """
        goal_lower = goal.lower()
        steps: list[tuple[str, str | None]] = []

        # Step 1: Always understand the goal
        steps.append((f"Understand and analyze the goal: '{goal}'", None))

        # Step 2: Detect tool-relevant actions
        for tool, keywords in self.TOOL_KEYWORDS.items():
            if tool in available_tools:
                for kw in keywords:
                    if kw in goal_lower:
                        steps.append((f"Use {tool} to: {goal}", tool))
                        break

        # Step 3: If multi-part (contains "and", "then", "also")
        conjunctions = ["and then", "then", " and ", "also", "after that"]
        for conj in conjunctions:
            if conj in goal_lower:
                parts = re.split(conj, goal_lower, flags=re.IGNORECASE)
                if len(parts) > 1:
                    for part in parts[1:]:
                        part = part.strip()
                        if part:
                            hint = self._detect_tool(part, available_tools)
                            steps.append((f"Execute: {part}", hint))
                    break

        # Step 4: Always summarize results
        steps.append(("Compile results and formulate final answer", None))

        return steps

    def _detect_tool(self, text: str, available_tools: list[str]) -> str | None:
        text_lower = text.lower()
        for tool, keywords in self.TOOL_KEYWORDS.items():
            if tool in available_tools:
                if any(kw in text_lower for kw in keywords):
                    return tool
        return None

    def update_step(self, plan: Plan, step_index: int, result: Any = None, error: str | None = None) -> None:
        """Mark a plan step as done or failed."""
        if step_index >= len(plan.steps):
            return
        step = plan.steps[step_index]
        if error:
            step.mark_failed(error)
        else:
            step.mark_done(result)
