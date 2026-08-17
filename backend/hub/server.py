"""
Hub Server Factory – FastAPI application setup
"""
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from rich.console import Console

from hub.config import settings
from hub.events import EventType, event_bus

console = Console()
logger  = logging.getLogger("xanax.server")

_frontend_dist_path = Path(__file__).resolve().parents[2] / "frontend" / "dist"


_NO_CACHE_HEADERS = {"Cache-Control": "no-store, must-revalidate"}


def _configuration_issues(*, creating_default_user: bool) -> list[str]:
    """Các cấu hình mặc định không an toàn khi đưa ứng dụng lên production."""
    issues = []
    fields = type(settings).model_fields
    if not settings.secret_key.strip() or settings.secret_key == fields["secret_key"].default:
        issues.append("HUB_SECRET_KEY vẫn là giá trị mặc định; hãy đặt một secret mạnh")
    if not settings.api_key.strip() or settings.api_key == fields["api_key"].default:
        issues.append("HUB_API_KEY vẫn là giá trị mặc định; hãy đặt một API key mạnh")
    if creating_default_user and (
        not settings.admin_pass.strip()
        or settings.admin_pass.strip() == fields["admin_pass"].default
    ):
        issues.append(
            "database chưa có người dùng và XANAX_ADMIN_PASS chưa được đặt hoặc vẫn là 'xanax'; "
            "hãy đặt mật khẩu quản trị mạnh"
        )
    return issues


class _NoCacheStatic(StaticFiles):
    """Static files served from a development build must never be stale."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers.update(_NO_CACHE_HEADERS)
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler – startup & shutdown."""
    console.print(f"[bold cyan]⚡ {settings.xanax_name} starting...[/]")

    # ── Database init ──────────────────────────────────────────
    from hub.database import (
        init_db, user_count, create_user, clear_all_sessions, purge_expired_sessions,
        recover_interrupted_experiments,
    )
    await init_db()
    creating_default_user = await user_count() == 0
    configuration_issues = _configuration_issues(
        creating_default_user=creating_default_user,
    )
    if configuration_issues:
        message = "Cấu hình không an toàn: " + "; ".join(configuration_issues) + "."
        if settings.is_production:
            raise RuntimeError("Không thể khởi động production. " + message)
        logger.warning(message)
        console.print(f"[bold yellow]⚠  {message}[/]")

    await recover_interrupted_experiments()
    await clear_all_sessions()  # force re-login after every server restart

    if creating_default_user:
        await create_user(settings.admin_user, settings.admin_pass)
        console.print("[bold yellow]⚠  No users found. Admin account created:[/]")
        console.print(f"   Username: [bold]{settings.admin_user}[/]")
        if settings.debug:
            console.print(f"   Password: [bold]{settings.admin_pass}[/]")
        else:
            console.print("   [dim]Password read from XANAX_ADMIN_PASS.[/]")

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
        docs_url="/api/docs" if settings.api_docs_enabled else None,
        redoc_url="/api/redoc" if settings.api_docs_enabled else None,
        openapi_url="/api/openapi.json" if settings.api_docs_enabled else None,
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
    from api.routes.experiments    import router as experiments_router
    from api.websocket            import router as ws_router
    from api.websocket_training   import router as ws_training_router
    from api.websocket_task       import router as ws_task_router
    from api.websocket_meeting    import router as ws_meeting_router
    from api.websocket_benchmark  import router as ws_benchmark_router
    from api.websocket_workflow   import router as ws_workflow_router
    from api.websocket_experiment import router as ws_experiment_router

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
    app.include_router(experiments_router,   prefix="/api/experiments",    tags=["Experiments"])
    app.include_router(ws_router,                                          tags=["WebSocket"])
    app.include_router(ws_training_router,                                 tags=["WebSocket"])
    app.include_router(ws_task_router,                                     tags=["WebSocket"])
    app.include_router(ws_meeting_router,                                  tags=["WebSocket"])
    app.include_router(ws_benchmark_router,                                tags=["WebSocket"])
    app.include_router(ws_workflow_router,                                 tags=["WebSocket"])
    app.include_router(ws_experiment_router,                               tags=["WebSocket"])

    # ── React production build ────────────────────────────────
    # Hashed Vite assets may be cached in production. During local development,
    # no-store avoids a stale build when testing FastAPI without the Vite server.
    static_class = _NoCacheStatic if settings.debug else StaticFiles
    frontend_assets = _frontend_dist_path / "assets"
    if frontend_assets.is_dir():
        app.mount("/assets", static_class(directory=frontend_assets), name="frontend-assets")

    frontend_images = _frontend_dist_path / "images"
    if frontend_images.is_dir():
        app.mount("/images", static_class(directory=frontend_images), name="frontend-images")

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
            "docs":          "/api/docs" if settings.api_docs_enabled else None,
        }

    # Keep this last. Known API/WS prefixes must never fall through to the SPA,
    # otherwise a missing endpoint quietly returns index.html with HTTP 200.
    @app.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
    async def serve_spa(path: str = ""):
        if path == "api" or path.startswith("api/") or path == "ws" or path.startswith("ws/"):
            raise HTTPException(status_code=404)

        segments = path.split("/")
        if any(segment.startswith(".") and segment != ".well-known" for segment in segments):
            raise HTTPException(status_code=404)

        # Yêu cầu trông như file chỉ được phục vụ khi đích đã phân giải vẫn nằm
        # trong dist. Kiểm tra trên đường dẫn resolve() cũng chặn symlink thoát ra ngoài.
        if Path(segments[-1]).suffix:
            try:
                dist = _frontend_dist_path.resolve()
                static_file = (dist / path).resolve()
                static_file.relative_to(dist)
            except (OSError, RuntimeError, ValueError):
                raise HTTPException(status_code=404)

            if static_file.is_file():
                return FileResponse(static_file)
            raise HTTPException(status_code=404)

        index = _frontend_dist_path / "index.html"
        if index.is_file():
            return FileResponse(index, media_type="text/html", headers=_NO_CACHE_HEADERS)
        return HTMLResponse(
            "<h1>React build not found</h1><p>Run npm run build in frontend/.</p>",
            status_code=404,
            headers=_NO_CACHE_HEADERS,
        )

    return app
