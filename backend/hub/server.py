"""
Hub Server Factory – FastAPI application setup
"""
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from rich.console import Console

from hub.config import settings
from hub.events import EventType, event_bus

console = Console()
logger  = logging.getLogger("xanax.server")

_dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard")
_frontend_dist_path = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _read_html(filename: str) -> str | None:
    path = os.path.join(_dashboard_path, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


_NO_CACHE_HEADERS = {"Cache-Control": "no-store, must-revalidate"}


def _html_response(html: str, status_code: int = 200) -> HTMLResponse:
    # Trang dashboard sửa liên tục trong lúc phát triển — không cho trình duyệt/iframe
    # cache lại bản cũ, tránh tình trạng đã sửa code nhưng vẫn thấy hành vi cũ.
    return HTMLResponse(html, status_code=status_code, headers=_NO_CACHE_HEADERS)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler – startup & shutdown."""
    console.print(f"[bold cyan]⚡ {settings.xanax_name} starting...[/]")

    # ── Database init ──────────────────────────────────────────
    from hub.database import init_db, user_count, create_user, clear_all_sessions, purge_expired_sessions
    await init_db()
    await clear_all_sessions()  # force re-login after every server restart

    if await user_count() == 0:
        default_user = os.environ.get("XANAX_ADMIN_USER", "admin")
        default_pass = os.environ.get("XANAX_ADMIN_PASS", "xanax")
        await create_user(default_user, default_pass)
        console.print(f"[bold yellow]⚠  No users found. Default account created:[/]")
        console.print(f"   Username: [bold]{default_user}[/]")
        console.print(f"   Password: [bold]{default_pass}[/]")
        console.print(f"   [dim]Set XANAX_ADMIN_USER / XANAX_ADMIN_PASS in .env to override.[/]")

    # ── Session purge task (every 30 min) ──────────────────────
    import asyncio

    async def _session_purge_loop():
        while True:
            await asyncio.sleep(1800)  # 30 minutes
            try:
                await purge_expired_sessions()
            except Exception:
                logger.exception("Session purge failed")

    purge_task = asyncio.create_task(_session_purge_loop())

    # ── Core services ──────────────────────────────────────────
    from core.orchestrator import orchestrator
    from core.scheduler import task_scheduler
    await orchestrator.start()
    await task_scheduler.start()

    from api.routes.workflow import restore_schedules, recover_interrupted_runs
    await recover_interrupted_runs()
    await restore_schedules()

    from core.soul_sync import sync_soul_md
    from core.skill_tools import sync_api_skill_tools
    from core.mcp_client import mcp_manager, sync_mcp_skill_tools

    async def _on_data_changed(event) -> None:
        await sync_soul_md()
        if event.data == "skills":
            await sync_api_skill_tools()
            await sync_mcp_skill_tools()

    event_bus.subscribe(EventType.DATA_CHANGED, _on_data_changed)
    await sync_soul_md()
    await sync_api_skill_tools()
    # Kết nối MCP server chạy nền: server stdio có thể mất vài giây nạp model,
    # không để nó chặn app khởi động.
    mcp_boot_task = asyncio.create_task(sync_mcp_skill_tools())

    await event_bus.emit_simple(EventType.SYSTEM_STARTUP, {"message": f"{settings.xanax_name} started"})
    console.print(f"[bold green]✓ {settings.xanax_name} ready![/]")

    yield  # ← server running

    purge_task.cancel()
    mcp_boot_task.cancel()

    console.print(f"[bold yellow]⏹ Shutting down {settings.xanax_name}...[/]")
    await task_scheduler.stop()
    await orchestrator.stop()
    # Tắt hẳn các tiến trình con MCP stdio, nếu không chúng thành tiến trình mồ côi.
    await mcp_manager.close_all()
    await event_bus.emit_simple(EventType.SYSTEM_SHUTDOWN, {"message": f"{settings.xanax_name} stopped"})
    console.print(f"[bold red]✗ {settings.xanax_name} stopped.[/]")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.xanax_name,
        version=settings.version,
        description=f"{settings.xanax_name} – Personal AI Agent powered by Hermes",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────
    # THỨ TỰ QUAN TRỌNG: add_middleware chèn vào đầu chuỗi, nên cái thêm SAU chạy
    # NGOÀI CÙNG. CORS phải nằm ngoài lớp gác xác thực — request preflight OPTIONS
    # của trình duyệt không bao giờ mang cookie, nếu để AuthGuard chộp trước thì
    # preflight nhận 401 và mọi lời gọi cross-origin đều hỏng.
    from api.auth_guard import AuthGuardMiddleware
    app.add_middleware(AuthGuardMiddleware)

    # settings.cors_origins trả [] khi debug=False. Trước đây thuộc tính này tồn
    # tại nhưng KHÔNG nơi nào dùng — CORS bị hardcode ["*"] kèm allow_credentials,
    # nghĩa là bất kỳ trang web nào cũng gọi API kèm cookie của người dùng được.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time"] = f"{elapsed:.2f}ms"
        return response

    # Added last so compression wraps every HTTP response, including static assets.
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ── API Routes ────────────────────────────────────────────
    from api.routes.health        import router as health_router
    from api.routes.agents        import router as agents_router
    from api.routes.tasks         import router as tasks_router
    from api.routes.tools         import router as tools_router
    from api.routes.chat          import router as chat_router
    from api.routes.auth          import router as auth_router
    from api.routes.training      import router as training_router
    from api.routes.task_sessions import router as task_sessions_router
    from api.routes.agent_configs import router as agent_configs_router
    from api.routes.departments   import router as departments_router
    from api.routes.skills_mgmt   import router as skills_router
    from api.routes.projects      import router as projects_router
    from api.routes.meetings      import router as meetings_router
    from api.routes.benchmarks    import router as benchmarks_router
    from api.routes.workflow       import router as workflow_router
    from api.routes.model_pool     import router as model_pool_router
    from api.routes.knowledge      import router as knowledge_router
    from api.routes.ops            import router as ops_router
    from api.routes.assets         import router as assets_router
    from api.websocket            import router as ws_router
    from api.websocket_training   import router as ws_training_router
    from api.websocket_task       import router as ws_task_router
    from api.websocket_meeting    import router as ws_meeting_router
    from api.websocket_benchmark  import router as ws_benchmark_router
    from api.websocket_workflow   import router as ws_workflow_router

    app.include_router(health_router,        prefix="/api",                tags=["Health"])
    app.include_router(agents_router,        prefix="/api/agents",         tags=["Agents"])
    app.include_router(tasks_router,         prefix="/api/tasks",          tags=["Tasks"])
    app.include_router(tools_router,         prefix="/api/tools",          tags=["Tools"])
    app.include_router(chat_router,          prefix="/api/chat",           tags=["Chat"])
    app.include_router(auth_router,          prefix="/api/auth",           tags=["Auth"])
    app.include_router(training_router,      prefix="/api/training",       tags=["Training"])
    app.include_router(task_sessions_router, prefix="/api/task-sessions",  tags=["Task Sessions"])
    app.include_router(agent_configs_router, prefix="/api/agent-configs",  tags=["Hub"])
    app.include_router(departments_router,   prefix="/api/departments",    tags=["Hub"])
    app.include_router(skills_router,        prefix="/api/skills",         tags=["Hub"])
    app.include_router(projects_router,      prefix="/api/projects",       tags=["Hub"])
    app.include_router(meetings_router,      prefix="/api/meetings",       tags=["Hub"])
    app.include_router(benchmarks_router,    prefix="/api/benchmarks",     tags=["Hub"])
    app.include_router(workflow_router,      prefix="/api/workflow",       tags=["Workflow"])
    app.include_router(model_pool_router,    prefix="/api/model-pool",     tags=["Model Pool"])
    app.include_router(knowledge_router,     prefix="/api/knowledge",      tags=["Knowledge"])
    app.include_router(ops_router,           prefix="/api/ops",            tags=["Project Ops"])
    app.include_router(assets_router,        prefix="/api/assets",         tags=["Assets"])
    app.include_router(ws_router,                                          tags=["WebSocket"])
    app.include_router(ws_training_router,                                 tags=["WebSocket"])
    app.include_router(ws_task_router,                                     tags=["WebSocket"])
    app.include_router(ws_meeting_router,                                  tags=["WebSocket"])
    app.include_router(ws_benchmark_router,                                tags=["WebSocket"])
    app.include_router(ws_workflow_router,                                 tags=["WebSocket"])

    # ── Static files ──────────────────────────────────────────
    if os.path.isdir(_dashboard_path):
        static_path = os.path.join(_dashboard_path, "static")
        if os.path.isdir(static_path):
            app.mount("/static", StaticFiles(directory=static_path), name="static")
    # React build (temporary Phase 1-5 route).
    # Legacy pages remain the default until their React replacements are accepted.
    # Vite emits hashed assets at /assets; /v2 serves the React shell in parallel.
    frontend_assets = _frontend_dist_path / "assets"
    if frontend_assets.is_dir():
        app.mount("/assets", StaticFiles(directory=frontend_assets), name="frontend-assets")

    @app.get("/v2", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/v2/{path:path}", response_class=HTMLResponse, include_in_schema=False)
    async def serve_react_build(path: str = ""):  # noqa: ARG001
        index = _frontend_dist_path / "index.html"
        if index.is_file():
            return FileResponse(index, media_type="text/html", headers=_NO_CACHE_HEADERS)
        return _html_response("<h1>React build not found</h1>", status_code=404)

    # ── Auth helper ───────────────────────────────────────────
    async def _is_authenticated(request: Request) -> bool:
        from hub.database import COOKIE_NAME, validate_session
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return False
        return await validate_session(token) is not None

    # ── Pages ─────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/login", response_class=HTMLResponse, include_in_schema=False)
    async def serve_login(request: Request):
        # If already logged in, skip login and go straight to hub
        if await _is_authenticated(request):
            return RedirectResponse(url="/hub", status_code=302)
        html = _read_html("login.html")
        if html:
            return _html_response(html)
        return _html_response("<h1>Login page not found</h1>", status_code=404)

    @app.get("/workspace", response_class=HTMLResponse, include_in_schema=False)
    async def serve_workspace(request: Request):
        if not await _is_authenticated(request):
            return RedirectResponse(url="/login", status_code=302)
        html = _read_html("workspace.html")
        if html:
            return _html_response(html)
        return _html_response("<h1>Workspace not found</h1>", status_code=404)

    @app.get("/taskrunner", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/taskrunner/{workflow_id}", response_class=HTMLResponse, include_in_schema=False)
    async def serve_taskrunner(request: Request, workflow_id: str = None):  # noqa: ARG001 (read client-side from location.pathname)
        if not await _is_authenticated(request):
            return RedirectResponse(url="/login", status_code=302)
        html = _read_html("taskrunner.html")
        if html:
            return _html_response(html)
        return _html_response("<h1>Task Runner not found</h1>", status_code=404)

    _HUB_TABS = {"home", "agents", "skills", "tasks", "meeting", "train", "company-runner", "auto-runner", "runner", "model", "cost", "settings"}

    @app.get("/hub", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/hub/{tab}", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/hub/{tab}/{subpath}", response_class=HTMLResponse, include_in_schema=False)
    async def serve_hub(request: Request, tab: str = "agents", subpath: str = None):
        if not await _is_authenticated(request):
            return RedirectResponse(url="/login", status_code=302)
        if tab not in _HUB_TABS:
            return RedirectResponse(url="/hub", status_code=302)
        html = _read_html("hub.html")
        if html:
            return _html_response(html)
        return _html_response("<h1>Hub not found</h1>", status_code=404)

    @app.get("/api", include_in_schema=False)
    async def api_root():
        from core.hermes_bridge import hermes
        hermes_alive = await hermes.is_alive()
        return {
            "name":          settings.xanax_name,
            "version":       settings.version,
            "chat_base_url": hermes.base_url,
            "chat_model":    hermes.model,
            "chat_online":   hermes_alive,
            "docs":          "/api/docs",
        }

    return app
