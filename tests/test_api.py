"""
Tests – FastAPI Routes (integration tests using httpx AsyncClient)
"""
import pytest
from httpx import AsyncClient, ASGITransport

from hub.server import create_app


@pytest.fixture
async def client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestHealthRoutes:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "uptime_seconds" in data

    @pytest.mark.asyncio
    async def test_readiness(self, client):
        resp = await client.get("/api/health/ready")
        assert resp.status_code == 200
        assert resp.json()["ready"] is True

    @pytest.mark.asyncio
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert data["status"] == "running"


class TestAgentRoutes:
    @pytest.mark.asyncio
    async def test_list_agents_empty(self, client):
        resp = await client.get("/api/agents/")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_spawn_agent(self, client):
        resp = await client.post("/api/agents/spawn", json={
            "task": "Test task for API testing",
            "agent_name": "test-agent",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "record_id" in data
        assert data["agent_name"] == "test-agent"

    @pytest.mark.asyncio
    async def test_spawn_agent_missing_task(self, client):
        resp = await client.post("/api/agents/spawn", json={"agent_name": "test"})
        assert resp.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client):
        resp = await client.get("/api/agents/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_agent_stats(self, client):
        resp = await client.get("/api/agents/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "running" in data


class TestToolRoutes:
    @pytest.mark.asyncio
    async def test_list_tools(self, client):
        resp = await client.get("/api/tools/")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_tool_not_found(self, client):
        resp = await client.get("/api/tools/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_call_tool(self, client):
        resp = await client.post("/api/tools/call", json={
            "name": "get_system_info",
            "args": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "result" in data


class TestTaskRoutes:
    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, client):
        resp = await client.get("/api/tasks/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_queue_stats(self, client):
        resp = await client.get("/api/tasks/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "queue_size" in data
