"""API Routes – Workflow Tasks, Runs, Outputs (CRUD + schedule management)"""
import json
import logging
import secrets

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from hub.database import (
    create_workflow_task, list_workflow_tasks, get_workflow_task,
    update_workflow_task, delete_workflow_task, list_workflow_tasks_by_trigger,
    create_workflow_run, list_workflow_runs, get_workflow_run, list_workflow_runs_by_status,
    delete_workflow_run, update_workflow_run_status,
    list_workflow_outputs, update_workflow_output, get_workflow_output,
)

router = APIRouter()
logger = logging.getLogger("xanax.routes.workflow")


# ── Pydantic models ────────────────────────────────────────────────────────────

class WorkflowTaskCreate(BaseModel):
    name: str = Field(..., min_length=1)
    kind: str = Field("automation", pattern="^(company|automation)$")
    description: str = Field("")
    project_id: int | None = None
    agents_json: str = Field("[]")
    graph_json: str = Field("")
    trigger_type: str = Field("manual")
    trigger_config_json: str = Field("{}")
    schedule_enabled: bool = False
    schedule_cron: str = Field("")


class WorkflowTaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    project_id: int | None = None
    agents_json: str | None = None
    graph_json: str | None = None
    trigger_type: str | None = None
    trigger_config_json: str | None = None
    schedule_enabled: bool | None = None
    schedule_cron: str | None = None
    status: str | None = None
    kind: str | None = Field(None, pattern="^(company|automation)$")


class OutputUpdate(BaseModel):
    pass_fail: str | None = None
    edited_content: str | None = None
    notes: str | None = None
    review_status: str | None = None


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.get("/tasks")
async def list_tasks(project_id: int | None = None, kind: str | None = None):
    if kind not in (None, "company", "automation"):
        raise HTTPException(422, "kind must be 'company' or 'automation'")
    tasks = await list_workflow_tasks(project_id=project_id, kind=kind)
    return {"tasks": tasks}


def _ensure_webhook_token(trigger_type: str, trigger_config_json: str) -> str:
    """Sinh token khi webhook là trigger chính hoặc được bật trong map multi-trigger."""
    try:
        cfg = json.loads(trigger_config_json or "{}")
    except Exception:
        cfg = {}
    webhook_cfg = cfg.get("triggers", {}).get("webhook", {})
    webhook_enabled = trigger_type == "webhook" or bool(webhook_cfg.get("enabled"))
    if webhook_enabled and not cfg.get("webhook_token"):
        cfg["webhook_token"] = secrets.token_urlsafe(16)
    if webhook_enabled:
        cfg.setdefault("triggers", {}).setdefault("webhook", {})["webhook_token"] = cfg.get("webhook_token")
    return json.dumps(cfg)


@router.post("/tasks", status_code=201)
async def create_task(body: WorkflowTaskCreate):
    trigger_config_json = _ensure_webhook_token(body.trigger_type, body.trigger_config_json)
    task_id = await create_workflow_task(
        name=body.name,
        description=body.description,
        project_id=body.project_id,
        agents_json=body.agents_json,
        graph_json=body.graph_json,
        trigger_type=body.trigger_type,
        trigger_config_json=trigger_config_json,
        schedule_enabled=1 if body.schedule_enabled else 0,
        schedule_cron=body.schedule_cron,
        kind=body.kind,
    )
    task = await get_workflow_task(task_id)
    if body.schedule_enabled and body.schedule_cron:
        await _register_schedule(task_id, body.schedule_cron)
    return task


def _synthesize_graph_from_agents(agents_json: str, trigger_type: str) -> dict:
    """Chuyển pipeline tuần tự cũ (agents_json) thành graph tương đương:
    1 node trigger nối tuần tự qua từng node agent theo đúng `order`."""
    try:
        agents = sorted(json.loads(agents_json or "[]"), key=lambda a: a.get("order", 0))
    except Exception:
        agents = []

    nodes = [{"id": "n1", "type": "trigger", "x": 60, "y": 40, "data": {"trigger_type": trigger_type or "manual"}}]
    edges = []
    prev_id = "n1"
    for i, a in enumerate(agents):
        node_id = f"n{i+2}"
        nodes.append({
            "id": node_id, "type": "agent", "x": 60, "y": 40 + (i + 1) * 90,
            "data": {
                "agent_id": a.get("agent_id"), "agent_name": a.get("agent_name", ""),
                "instructions": a.get("instructions", ""),
                "use_rag": bool(a.get("use_rag")),
            },
        })
        edges.append({"from": prev_id, "to": node_id, "branch": None})
        prev_id = node_id

    return {"nodes": nodes, "edges": edges}


@router.get("/tasks/{task_id}")
async def get_task(task_id: int):
    task = await get_workflow_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    # Migrate quy trình cũ (danh sách tuần tự) sang graph ngay lần đầu mở —
    # từ nay sơ đồ là định dạng duy nhất được UI hiển thị/chỉnh sửa.
    if not (task.get("graph_json") or "").strip():
        try:
            agents = json.loads(task.get("agents_json") or "[]")
        except Exception:
            agents = []
        if agents:
            graph = _synthesize_graph_from_agents(task.get("agents_json", "[]"), task.get("trigger_type", "manual"))
            await update_workflow_task(task_id, graph_json=json.dumps(graph))
            task = await get_workflow_task(task_id)

    return task


@router.patch("/tasks/{task_id}")
async def update_task(task_id: int, body: WorkflowTaskUpdate):
    task = await get_workflow_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    kwargs = {}
    for field_name in body.model_fields_set:
        val = getattr(body, field_name)
        if field_name == "schedule_enabled":
            kwargs[field_name] = 1 if val else 0
        else:
            kwargs[field_name] = val

    # Sinh webhook token nếu webhook là trigger chính hoặc được bật trong map.
    new_trigger_type = kwargs.get("trigger_type", task.get("trigger_type"))
    base_cfg = kwargs.get("trigger_config_json", task.get("trigger_config_json", "{}"))
    ensured_cfg = _ensure_webhook_token(new_trigger_type, base_cfg)
    if ensured_cfg != base_cfg or "trigger_config_json" in kwargs:
        kwargs["trigger_config_json"] = ensured_cfg

    if kwargs:
        await update_workflow_task(task_id, **kwargs)

    updated = await get_workflow_task(task_id)
    if updated.get("status") == "active" and updated["schedule_enabled"] and updated["schedule_cron"]:
        await _register_schedule(task_id, updated["schedule_cron"])
    else:
        await _remove_schedule(task_id)

    return updated


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    if not await delete_workflow_task(task_id):
        raise HTTPException(404, "Task not found")
    await _remove_schedule(task_id)


# ── Runs ──────────────────────────────────────────────────────────────────────

@router.get("/runs")
async def list_runs(task_id: int | None = None, project_id: int | None = None, limit: int = 50):
    runs = await list_workflow_runs(task_id=task_id, project_id=project_id, limit=limit)
    return {"runs": runs}


@router.get("/runs/{run_id}")
async def get_run(run_id: int):
    run = await get_workflow_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    outputs = await list_workflow_outputs(run_id)
    return {**run, "outputs": outputs}


@router.delete("/runs/{run_id}", status_code=204)
async def delete_run(run_id: int):
    if not await delete_workflow_run(run_id):
        raise HTTPException(404, "Run not found")


@router.get("/runs/{run_id}/archive-file")
async def get_run_archive_file(run_id: int, path: str):
    """Tải 1 file (ảnh/text) đã được lưu trong thư mục archive của lần chạy
    này — xem core/project_storage.py. Dùng cho <img src> hiển thị ảnh sinh ra
    trong lúc chạy quy trình, và cho việc tải file archive về sau."""
    from fastapi.responses import FileResponse
    from core.project_storage import get_or_create_run_dir

    try:
        run_dir = (await get_or_create_run_dir(run_id)).resolve()
    except ValueError:
        raise HTTPException(404, "Run not found")
    target = (run_dir / path).resolve()
    if run_dir not in target.parents or not target.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(target)


# ── Outputs ───────────────────────────────────────────────────────────────────

@router.patch("/outputs/{output_id}")
async def update_output(output_id: int, body: OutputUpdate):
    kwargs: dict = {}
    for field_name in body.model_fields_set:
        kwargs[field_name] = getattr(body, field_name)
    if kwargs:
        await update_workflow_output(output_id, **kwargs)

    # Duyệt/từ chối một node approval_gate chỉ có tác dụng khi lần chạy vẫn còn
    # sống trong tiến trình này (waiter nằm trong RAM). Sau khi server khởi động
    # lại thì waiter mất — phải nói thẳng ra thay vì im lặng để người dùng tưởng
    # là quy trình đã chạy tiếp.
    resumed: bool | None = None
    if body.review_status in ("approved", "rejected"):
        from api.websocket_workflow import signal_workflow_approval
        resumed = signal_workflow_approval(
            output_id,
            approved=body.review_status == "approved",
            edited_content=body.edited_content if body.review_status == "approved" else None,
        )
        if not resumed:
            output = await get_workflow_output(output_id)
            run = await get_workflow_run(output["run_id"]) if output and output.get("run_id") else None
            if run and run.get("status") == "running":
                await update_workflow_run_status(run["id"], "failed")
                await update_workflow_output(
                    output_id, review_status="needs_revision",
                    output_content=(output.get("output_content") or ""),
                )
                raise HTTPException(
                    409,
                    "Lần chạy này không còn sống (server đã khởi động lại từ lúc nó chờ duyệt) "
                    "nên không thể chạy tiếp. Đã đánh dấu thất bại — hãy chạy lại quy trình.",
                )

    # Khi có pass/fail → ghi vào SOUL.md chung để Xanax học, VÀ vào soul.md riêng của
    # đúng nhân viên đã tạo ra output đó (xem core/agent_soul.py) để nhân viên tự cải
    # thiện qua các lần làm việc tiếp theo.
    if body.pass_fail in ("pass", "fail"):
        output = await get_workflow_output(output_id)
        if output:
            from core.soul_sync import append_feedback_to_soul
            import asyncio
            asyncio.get_event_loop().run_in_executor(
                None, append_feedback_to_soul, output
            )
            if output.get("agent_id"):
                from core.agent_soul import append_feedback
                asyncio.get_event_loop().run_in_executor(
                    None, append_feedback, output["agent_id"], output.get("agent_name", ""),
                    output.get("task_name", ""), body.pass_fail,
                    output.get("edited_content") or output.get("output_content") or "",
                    output.get("notes") or "",
                )

    return {"ok": True}


# ── Webhook trigger (n8n-style) ─────────────────────────────────────────────

@router.post("/hooks/{token}")
async def trigger_via_webhook(token: str, request: Request):
    """Entry point cho trigger bên ngoài (curl, n8n thật, Zapier...). Không cần auth
    vì token đóng vai trò bí mật duy nhất cho từng workflow."""
    try:
        payload = await request.json()
        body_text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    except Exception:
        raw = await request.body()
        body_text = raw.decode("utf-8", errors="ignore")

    tasks = await list_workflow_tasks_by_trigger("webhook")
    target = None
    for t in tasks:
        try:
            cfg = json.loads(t.get("trigger_config_json") or "{}")
        except Exception:
            cfg = {}
        if cfg.get("webhook_token") == token:
            target = t
            break

    if not target:
        raise HTTPException(404, "Webhook không tồn tại")

    import asyncio
    from api.websocket_workflow import execute_workflow_headless
    asyncio.create_task(execute_workflow_headless(target["id"], user_input=body_text, triggered_by="webhook"))
    return {"ok": True, "task_id": target["id"], "task_name": target["name"]}


# ── Schedule helpers ──────────────────────────────────────────────────────────

async def _register_schedule(task_id: int, cron: str) -> None:
    try:
        from core.scheduler import task_scheduler

        async def _trigger():
            from api.websocket_workflow import execute_workflow_headless
            await execute_workflow_headless(task_id)

        await task_scheduler.schedule_cron(f"workflow_{task_id}", _trigger, cron)
        logger.info("Registered schedule for task %s: %s", task_id, cron)
    except Exception:
        logger.exception("Failed to register schedule for task %s", task_id)


async def _remove_schedule(task_id: int) -> None:
    try:
        from core.scheduler import task_scheduler
        await task_scheduler.remove_job(f"workflow_{task_id}")
    except Exception:
        pass


# ── Startup: restore schedules ────────────────────────────────────────────────

async def recover_interrupted_runs() -> None:
    """Dọn các lần chạy còn treo 'running' từ trước khi server tắt.

    Trạng thái chờ duyệt của node approval_gate nằm trong RAM (_approval_waiters),
    khởi động lại là mất — lần chạy không thể tiếp tục. Nếu để nguyên 'running'
    thì hàng chờ duyệt hiển thị sai và người dùng bấm duyệt mãi không có gì xảy ra.
    """
    try:
        stale = await list_workflow_runs_by_status("running")
        for run in stale:
            await update_workflow_run_status(run["id"], "failed")
            for output in await list_workflow_outputs(run["id"]):
                if output.get("review_status") == "waiting_review":
                    await update_workflow_output(output["id"], review_status="needs_revision")
        if stale:
            logger.warning(
                "Đã đánh dấu thất bại %d lần chạy bị ngắt giữa chừng do server khởi động lại",
                len(stale),
            )
    except Exception:
        logger.exception("Không dọn được các lần chạy bị ngắt giữa chừng")


async def restore_schedules() -> None:
    """Call on app startup to re-register all enabled task schedules."""
    try:
        tasks = await list_workflow_tasks()
        for task in tasks:
            if task.get("status") == "active" and task.get("schedule_enabled") and task.get("schedule_cron"):
                await _register_schedule(task["id"], task["schedule_cron"])
    except Exception:
        logger.exception("Failed to restore workflow schedules")
