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
    async def test_provider_health_requires_auth(self, anon_client):
        # Route này gọi CLI thật và tốn token, tuyệt đối không nằm trong
        # allowlist công khai của health/readiness.
        assert (await anon_client.post("/api/health/providers")).status_code == 401

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
    async def test_health_uptime_ignores_wall_clock_jump(self, monkeypatch):
        from api.routes import health

        monkeypatch.setattr(health, "_start_time", 100.0)
        monkeypatch.setattr(health.time, "monotonic", lambda: 101.25)
        # Mô phỏng NTP kéo đồng hồ tường lùi 7 giờ sau khi service khởi động.
        wall_times = iter((25_200.0, 0.0))
        monkeypatch.setattr(health.time, "time", lambda: next(wall_times))

        wall_before = health.time.time()
        data = await health.health_check()
        wall_after = health.time.time()

        assert wall_after < wall_before
        assert data["uptime_seconds"] == 1.25
        assert data["uptime_seconds"] >= 0

        monkeypatch.setattr(health.time, "monotonic", lambda: 99.0)
        assert (await health.health_check())["uptime_seconds"] == 0
        assert health._format_uptime(0) == "0h 0m 0s"

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
    async def test_provider_health_ignores_non_cli_pool(self, client, monkeypatch):
        from api.routes import health
        from hub.database import create_model_pool_entry

        await create_model_pool_entry(
            name="HTTP không thuộc probe",
            provider="9router",
            api_style="openai_compat",
            model_id="some-http-model",
        )

        calls = []

        async def fake_test(entry_id):
            calls.append(entry_id)
            return {"ok": True}

        monkeypatch.setattr(health, "test_model_connection", fake_test)
        resp = await client.post("/api/health/providers")

        assert resp.status_code == 200
        assert resp.json() == {
            "ok": True,
            "total": 0,
            "failures": [],
            "results": [],
        }
        assert calls == []

    @pytest.mark.asyncio
    async def test_provider_health_returns_503_for_failed_cli(self, client, monkeypatch):
        from api.routes import health
        from hub.database import create_model_pool_entry

        entry_id = await create_model_pool_entry(
            name="Claude chính",
            provider="claude",
            api_style="claude_cli",
            model_id="claude-sonnet",
            cli_config_dir="/home/xanax/.claude-papa",
        )

        calls = []

        async def fake_test(called_id):
            calls.append(called_id)
            return {
                "ok": False,
                "error": "OPENAI_API_KEY=rat-bi-mat /home/xanax/.claude-papa/credentials.json hết hạn",
            }

        monkeypatch.setattr(health, "test_model_connection", fake_test)
        resp = await client.post("/api/health/providers")

        assert resp.status_code == 503
        data = resp.json()
        assert data["ok"] is False
        assert data["total"] == 1
        assert len(data["failures"]) == 1
        assert data["failures"][0]["id"] == entry_id
        assert data["failures"][0]["api_style"] == "claude_cli"
        assert "rat-bi-mat" not in resp.text
        assert "/home/xanax" not in resp.text
        assert calls == [entry_id]

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


class TestVersionRoute:
    @pytest.mark.asyncio
    async def test_cong_khai_chi_tra_version_tu_settings(self, anon_client):
        """Trang đăng nhập lấy đúng nguồn version nhưng không thấy dấu vân tay Git."""
        from hub.config import settings

        resp = await anon_client.get("/api/version")
        assert resp.status_code == 200
        assert resp.json() == {"version": settings.version}

    @pytest.mark.asyncio
    async def test_git_hong_tra_null_khong_loi_500(self, client, monkeypatch):
        """Deploy từ tarball hoặc máy không có Git vẫn phải trả response hợp lệ."""
        from api.routes import version

        def git_khong_ton_tai(*_args, **_kwargs):
            raise FileNotFoundError("không có git")

        monkeypatch.setattr(version.subprocess, "run", git_khong_ton_tai)
        version.get_git_commit.cache_clear()
        try:
            resp = await client.get("/api/version")
            assert resp.status_code == 200
            assert resp.json() == {"version": version.settings.version, "commit": None}
        finally:
            # Không để giá trị mô phỏng ảnh hưởng các app được tạo sau test này.
            version.get_git_commit.cache_clear()


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
