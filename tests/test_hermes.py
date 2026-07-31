"""
Tests – Hermes Agent Core
"""
import asyncio
import pytest

from core.hermes.context import AgentContext, AgentStatus
from core.hermes.memory import AgentMemory, ShortTermMemory
from core.hermes.tool_registry import ToolRegistry
from core.hermes.planner import HermesPlanner
from core.hermes.agent import HermesAgent


# ── Context tests ──────────────────────────────────────────────
class TestAgentContext:
    def test_initial_state(self):
        ctx = AgentContext(task="test task")
        assert ctx.status == AgentStatus.IDLE
        assert not ctx.is_done
        assert not ctx.has_exceeded_limit

    def test_add_thought(self):
        ctx = AgentContext(task="test")
        thought = ctx.add_thought("I am thinking")
        assert len(ctx.thoughts) == 1
        assert thought.content == "I am thinking"

    def test_is_done_when_error(self):
        ctx = AgentContext(task="test")
        ctx.set_status(AgentStatus.ERROR)
        assert ctx.is_done

    def test_exceeded_limit(self):
        ctx = AgentContext(task="test", max_iterations=3)
        ctx.iteration = 3
        assert ctx.has_exceeded_limit


# ── Memory tests ───────────────────────────────────────────────
class TestShortTermMemory:
    @pytest.mark.asyncio
    async def test_set_get(self):
        mem = ShortTermMemory()
        await mem.set("key1", "value1")
        assert await mem.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        mem = ShortTermMemory()
        await mem.set("expiring", "data", ttl=0.01)
        await asyncio.sleep(0.05)
        assert await mem.get("expiring") is None

    @pytest.mark.asyncio
    async def test_delete(self):
        mem = ShortTermMemory()
        await mem.set("k", "v")
        assert await mem.delete("k") is True
        assert await mem.get("k") is None

    @pytest.mark.asyncio
    async def test_tag_search(self):
        mem = ShortTermMemory()
        await mem.set("a", 1, tags=["important"])
        await mem.set("b", 2, tags=["other"])
        results = await mem.search_by_tag("important")
        assert len(results) == 1
        assert results[0].key == "a"


# ── Tool Registry tests ────────────────────────────────────────
class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()

        @registry.register(name="test_tool", description="A test tool")
        async def my_tool(query: str) -> str:
            return f"Result: {query}"

        tool = registry.get("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.is_async is True

    @pytest.mark.asyncio
    async def test_call_tool(self):
        registry = ToolRegistry()

        @registry.register(name="echo", description="Echo tool")
        async def echo(message: str) -> str:
            return message

        result = await registry.call("echo", {"message": "hello"})
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_call_missing_tool(self):
        registry = ToolRegistry()
        with pytest.raises(ValueError, match="not found"):
            await registry.call("nonexistent", {})

    def test_schema_generation(self):
        registry = ToolRegistry()

        @registry.register(name="schema_test", description="Schema test")
        async def schema_test(x: str, y: int) -> str:
            return str(x) + str(y)

        schemas = registry.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "schema_test"
        assert "x" in schemas[0]["parameters"]["properties"]


# ── Planner tests ──────────────────────────────────────────────
class TestHermesPlanner:
    @pytest.mark.asyncio
    async def test_creates_plan(self):
        planner = HermesPlanner()
        plan = await planner.create_plan("Search for Python tutorials", ["web_search"])
        assert len(plan.steps) > 0
        assert plan.goal == "Search for Python tutorials"

    @pytest.mark.asyncio
    async def test_plan_progress(self):
        planner = HermesPlanner()
        plan = await planner.create_plan("test task", [])
        initial_progress = plan.progress
        # Mark first step done
        if plan.steps:
            plan.steps[0].mark_done("result")
        assert plan.progress >= initial_progress


# ── Agent integration test ─────────────────────────────────────
class TestHermesAgent:
    @pytest.mark.asyncio
    async def test_agent_runs_task(self):
        registry = ToolRegistry()
        agent = HermesAgent(name="test-hermes", registry=registry, max_iterations=3)
        ctx = await agent.run("Simple test task with no tools needed")
        assert ctx is not None
        assert ctx.status == AgentStatus.DONE
        assert ctx.final_answer is not None

    @pytest.mark.asyncio
    async def test_agent_with_tool(self):
        registry = ToolRegistry()

        @registry.register(name="mock_search", description="Mock search", tags=["web", "search"])
        async def mock_search(query: str) -> dict:
            return {"result": f"Mock results for: {query}"}

        agent = HermesAgent(name="test-agent", registry=registry, max_iterations=5)
        events_received = []

        async def capture_event(event_type: str, data):
            events_received.append(event_type)

        agent.on_event(capture_event)
        ctx = await agent.run("Search for information about AI")
        assert ctx.status == AgentStatus.DONE
        assert len(events_received) > 0
