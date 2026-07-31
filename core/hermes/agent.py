"""
HermesAgent – Core AI Agent with Perceive → Plan → Act → Reflect loop
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

from core.hermes.context import AgentContext, AgentStatus, Action
from core.hermes.memory import AgentMemory
from core.hermes.planner import HermesPlanner, Plan
from core.hermes.tool_registry import ToolRegistry, tool_registry as global_registry
from hub.config import settings

logger = logging.getLogger("hermes.agent")


class HermesAgent:
    """
    The Hermes Agent – a ReAct-style agent with:
      • Perceive  – observe the task & environment
      • Plan      – decompose into steps
      • Act       – call tools & execute steps
      • Reflect   – evaluate results, update memory

    Can be run as a standalone agent or as a sub-agent under the Orchestrator.
    """

    def __init__(
        self,
        name: str = "hermes",
        agent_id: str | None = None,
        registry: ToolRegistry | None = None,
        max_iterations: int | None = None,
    ):
        self.name = name
        self.registry = registry or global_registry
        self.memory = AgentMemory(agent_id or name)
        self.planner = HermesPlanner()
        self._ctx: AgentContext | None = None
        self._plan: Plan | None = None
        self._max_iterations = max_iterations or settings.hermes_max_iterations
        self._event_callbacks: list[Callable[[str, Any], Coroutine]] = []
        self._running = False

    # ── Public API ─────────────────────────────────────────────────────────

    async def run(self, task: str, session_id: str = "default") -> AgentContext:
        """
        Execute a task. Returns the final AgentContext with results.
        """
        ctx = AgentContext(
            agent_name=self.name,
            task=task,
            max_iterations=self._max_iterations,
        )
        if self._ctx is None:
            self._ctx = ctx
        self._running = True

        self.memory.add_user_message(task, session=session_id)
        await self._emit("agent_started", {"task": task, "agent": self.name})

        try:
            # ── Perceive ──
            ctx.set_status(AgentStatus.THINKING)
            ctx.add_thought(f"Received task: {task}")
            await self._emit("thought", ctx.thoughts[-1].to_dict())

            # ── Plan ──
            available_tools = [t.name for t in self.registry.list_tools()]
            self._plan = await self.planner.create_plan(task, available_tools)
            ctx.plan = [s.description for s in self._plan.steps]
            ctx.add_thought(f"Created plan with {len(self._plan.steps)} steps")
            await self._emit("plan_updated", self._plan.to_dict())

            # ── Act / Reflect loop ──
            while not ctx.is_done and not ctx.has_exceeded_limit and self._running:
                ctx.iteration += 1

                step = self._plan.current_step
                if step is None:
                    # All steps done
                    break

                ctx.set_status(AgentStatus.ACTING)
                ctx.add_thought(f"[Step {step.index + 1}] {step.description}")
                await self._emit("thought", ctx.thoughts[-1].to_dict())

                # Execute step
                result = await self._execute_step(ctx, step)

                # Reflect
                ctx.set_status(AgentStatus.THINKING)
                reflection = f"Step {step.index + 1} completed" if not step.error else f"Step {step.index + 1} failed: {step.error}"
                ctx.add_thought(reflection)

                if self._plan.is_complete or self._plan.has_failed:
                    break

            # ── Final Answer ──
            ctx.final_answer = self._synthesize_answer(ctx)
            ctx.set_status(AgentStatus.DONE)
            self.memory.add_assistant_message(ctx.final_answer or "", session=session_id)
            await self._emit("agent_done", {"answer": ctx.final_answer})

        except asyncio.CancelledError:
            ctx.set_status(AgentStatus.STOPPED)
            ctx.error = "Agent was cancelled"
            raise
        except Exception as e:
            ctx.set_status(AgentStatus.ERROR)
            ctx.error = str(e)
            logger.exception("HermesAgent error")
            await self._emit("agent_error", {"error": str(e)})
        finally:
            self._running = False

        return ctx

    async def stop(self) -> None:
        """Signal the agent to stop after the current iteration."""
        self._running = False
        if self._ctx:
            self._ctx.set_status(AgentStatus.STOPPED)

    def on_event(self, callback: Callable[[str, Any], Coroutine]) -> None:
        """Register a callback to be called on agent events."""
        self._event_callbacks.append(callback)

    # ── Internal ───────────────────────────────────────────────────────────

    async def _execute_step(self, ctx: AgentContext, step) -> Any:
        """Execute a single plan step, calling a tool if one is hinted."""
        tool_name = step.tool_hint

        if tool_name and tool_name in self.registry:
            action = ctx.add_action(tool_name, {"query": ctx.task})
            await self._emit("action", action.to_dict())
            try:
                result = await self.registry.call(tool_name, {"query": ctx.task})
                action.result = result
                self.planner.update_step(self._plan, step.index, result=result)
                await self.memory.remember(f"step_{step.index}_result", result)
                await self._emit("observation", {"tool": tool_name, "result": str(result)[:500]})
                return result
            except Exception as e:
                action.error = str(e)
                self.planner.update_step(self._plan, step.index, error=str(e))
                logger.warning("Tool '%s' failed: %s", tool_name, e)
                return None
        else:
            # No tool – mark step as done (reasoning-only)
            self.planner.update_step(self._plan, step.index, result="Reasoning step completed")
            return None

    def _synthesize_answer(self, ctx: AgentContext) -> str:
        """Combine results from all completed steps into a final answer."""
        completed = [s for s in (self._plan.steps if self._plan else []) if s.result]
        if completed:
            parts = [f"Step {s.index + 1}: {str(s.result)[:300]}" for s in completed]
            return "Task completed.\n\n" + "\n".join(parts)
        return f"Task '{ctx.task}' processed in {ctx.iteration} iterations."

    async def _emit(self, event_type: str, data: Any) -> None:
        if self._event_callbacks:
            await asyncio.gather(
                *[cb(event_type, data) for cb in self._event_callbacks],
                return_exceptions=True,
            )

    @property
    def context(self) -> AgentContext | None:
        return self._ctx

    @property
    def is_running(self) -> bool:
        return self._running

    def status_dict(self) -> dict:
        return {
            "name": self.name,
            "is_running": self._running,
            "tools_count": len(self.registry),
            "memory": self.memory.to_dict(),
            "context": self._ctx.to_dict() if self._ctx else None,
        }
