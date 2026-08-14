"""
Tests – FastAPI Routes (integration tests using httpx AsyncClient)
"""
import pytest
from httpx import AsyncClient, ASGITransport

from hub.server import create_app


# /api/* và /ws/* nay được gác bởi api/auth_guard.py, nên test tích hợp phải đăng
# nhập thật thì mới gọi được — giống hệt cách giao diện hoạt động.
_TEST_USER = "_pytest_user"
_TEST_PASS = "pytest-only-do-not-reuse"


@pytest.fixture
async def anon_client():
    """Client CHƯA đăng nhập — dùng cho trang công khai và để kiểm tra bị chặn."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def client():
    """Client ĐÃ đăng nhập.

    Tài khoản test được tạo rồi xoá ngay sau mỗi test: để lại một user với mật
    khẩu nằm sẵn trong mã nguồn thì chính nó thành cửa sau.
    """
    import aiosqlite
    from hub.database import DB_PATH, create_user, get_user_by_username, init_db

    await init_db()
    if not await get_user_by_username(_TEST_USER):
        await create_user(_TEST_USER, _TEST_PASS)

    app = create_app()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/auth/login",
                                json={"username": _TEST_USER, "password": _TEST_PASS})
            assert resp.status_code == 200, f"Đăng nhập cho test thất bại: {resp.text}"
            yield c
    finally:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM users WHERE username = ?", (_TEST_USER,))
            await db.commit()


class TestAuthGuard:
    """Xem api/auth_guard.py. Trước khi có lớp này, 9/10 endpoint nhạy cảm trả 200
    cho người gọi không đăng nhập, và POST /api/skills/ tạo được bản ghi mới."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", [
        "/api/skills/", "/api/agent-configs/", "/api/projects/",
        "/api/meetings/", "/api/tools/", "/api/openapi.json",
    ])
    async def test_api_requires_auth(self, anon_client, path):
        assert (await anon_client.get(path)).status_code == 401

    @pytest.mark.asyncio
    async def test_write_requires_auth(self, anon_client):
        resp = await anon_client.post("/api/skills/", json={
            "name": "_should_not_exist", "description": "", "type": "custom", "config": {},
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", ["/api/health", "/api/health/ready"])
    async def test_health_stays_public(self, anon_client, path):
        """Probe của reverse proxy/uptime monitor không có cookie phiên."""
        response = await anon_client.get(path)
        assert response.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_webhook_stays_public(self, anon_client):
        """Trigger từ n8n/Zapier xác thực bằng token trong URL, không có cookie.
        404 = đã tới được route (token bịa không khớp workflow nào)."""
        resp = await anon_client.post("/api/workflow/hooks/khong-co-token-nay", json={})
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_authenticated_client_passes(self, client):
        assert (await client.get("/api/skills/")).status_code == 200


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
    async def test_readiness(self, client, monkeypatch):
        from core.orchestrator import orchestrator
        from core.scheduler import task_scheduler

        monkeypatch.setattr(type(orchestrator), "started", property(lambda self: True))
        monkeypatch.setattr(type(task_scheduler), "scheduler_running", property(lambda self: True))
        monkeypatch.setattr(type(task_scheduler), "worker_pool_running", property(lambda self: True))
        resp = await client.get("/api/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ready"] is True
        assert data["checks"] == {
            "database": True,
            "orchestrator": True,
            "scheduler": True,
            "task_queue": True,
        }

    @pytest.mark.asyncio
    async def test_root(self, anon_client):
        """`/` phục vụ trang đăng nhập (HTML), không phải JSON.

        Test này trước đây kỳ vọng JSON {"name", "status"} và đã hỏng từ lâu —
        hub/server.py gắn `/` vào serve_login trả HTMLResponse. Cập nhật cho khớp
        hành vi thật thay vì để nó đỏ mãi.
        """
        resp = await anon_client.get("/")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/html")


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
