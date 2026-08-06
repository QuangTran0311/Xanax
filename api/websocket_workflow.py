"""
WebSocket endpoint for Workflow task execution.

Hỗ trợ 2 chế độ:
  - Legacy tuyến tính: workflow_tasks.agents_json (danh sách bước, chạy tuần tự)
  - Graph (n8n-style): workflow_tasks.graph_json = {"nodes":[...], "edges":[...]}
    Node types: trigger | agent | condition | workflow_call | tool_call |
                set_data | delay | stop_error | approval_gate | noop

Một quy trình sau khi chạy xong sẽ tự động trigger các quy trình khác có
trigger_type='workflow_complete' trỏ về nó (xem _chain_downstream) — đây là
cơ chế "gửi result sang quy trình khác" mà không cần can thiệp thủ công.

Protocol (client → server):
  {"action": "run",    "task_id": N, "project_id": N|null}  — start executing a task;
                                                                project_id (tuỳ chọn) ghi đè
                                                                dự án mặc định của task cho
                                                                riêng lần chạy này, để 1 quy
                                                                trình dùng chung được cho
                                                                nhiều dự án khác nhau
  {"action": "cancel", "run_id": N}        — cancel an in-progress run

Protocol (server → client):
  {"type": "run_started",  "run_id": N, "task_name": "...", "steps": [...]}
  {"type": "agent_start",  "run_id": N, "step": N, "agent_name": "...", "agent_id": N, "output_id": N, "node_id": "..." | null}
  {"type": "agent_chunk",  "run_id": N, "step": N, "content": "..."}
  {"type": "agent_done",   "run_id": N, "step": N, "output_id": N, "node_id": "..." | null}
  {"type": "agent_error",  "run_id": N, "step": N, "content": "...", "node_id": "..." | null}
  {"type": "condition_result", "run_id": N, "node_id": "...", "result": true|false}
  {"type": "run_paused_for_approval", "run_id": N, "node_id": "...", "output_id": N,
                            "content": "...", "images": ["/api/..."], "note": "...", "approver": "CEO"}
                            — content: chỉ nội dung bài (đã bỏ khối IMAGE PROMPT/TỶ LỆ và
                              markdown ảnh); images: URL ảnh để client hiện ảnh thật
  {"type": "approval_rejected", "run_id": N, "node_id": "...", "output_id": N, "attempt": N}
  {"type": "approval_resumed",  "run_id": N, "node_id": "...", "output_id": N}
  {"type": "run_done",     "run_id": N}
  {"type": "run_cancelled","run_id": N}
  {"type": "run_error",    "run_id": N, "content": "..."}
  {"type": "error",        "content": "..."}
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable, Awaitable
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from hub.database import (
    get_workflow_task, get_agent_config, get_project, get_skill,
    create_workflow_run, update_workflow_run_status, get_workflow_run,
    create_workflow_output, update_workflow_output, list_workflow_outputs,
    list_workflow_tasks_by_trigger, create_ops_history, add_meeting_message,
)
from core.hermes_bridge import hermes
from core.rag import rag_search, format_rag_context

router = APIRouter()
logger = logging.getLogger("xanax.websocket_workflow")

# cancel flags keyed by run_id
_cancel_flags: dict[int, bool] = {}
# output_id -> {"event": asyncio.Event, "approved": bool|None, "edited_content": str|None}
_approval_waiters: dict[int, dict] = {}

# Nhịp kiểm tra vòng chờ duyệt (giây). Tách thành hằng số để test rút ngắn được
# thay vì phải chờ hết hạn thật.
_APPROVAL_POLL_SECONDS = 1.0

# Error patterns that providers stream as content instead of raising HTTP errors
_STREAM_ERROR_PREFIXES = ("[Error]", "[Hermes error:", "[Xanax error:")


class _GraphStepError(Exception):
    """Một node làm quy trình dừng. `notified=True` khi sự kiện run_failed đã
    được gửi tại chỗ, để lớp ngoài không gửi trùng."""

    def __init__(self, message: str = "", notified: bool = False) -> None:
        super().__init__(message)
        self.notified = notified


# ── Chạy ngầm: run sống độc lập với tab trình duyệt ───────────────────────────
#
# Một lần chạy KHÔNG thuộc về websocket nào cả. Nó chạy trong một asyncio.Task
# riêng và đẩy sự kiện vào _RunSession bên dưới. Websocket chỉ là "người xem":
# đóng tab / mất mạng / chuyển tab chỉ làm mất người xem, luồng chạy vẫn tiếp
# tục tới khi xong. Khi người dùng quay lại, client gọi action "attach" để phát
# lại toàn bộ sự kiện đã xảy ra rồi xem tiếp theo thời gian thực.

# Giữ tối đa bấy nhiêu sự kiện cho mỗi lần chạy để phát lại (tránh phình bộ nhớ
# với những run rất dài — sự kiện cũ nhất bị bỏ trước).
_REPLAY_BUFFER_LIMIT = 4000
# Giữ session đã chạy xong bấy nhiêu giây để người dùng quay lại còn thấy kết quả.
_FINISHED_SESSION_TTL = 900


class _RunSession:
    """Kênh phát sự kiện của một lần chạy, tách rời khỏi websocket."""

    def __init__(self, task_id: int, task_name: str = "") -> None:
        self.task_id = task_id
        self.task_name = task_name
        self.run_id: int | None = None
        self.events: list[dict] = []
        self.subscribers: set[Callable[[dict], Awaitable[None]]] = set()
        self.finished = False
        self.task: asyncio.Task | None = None

    async def publish(self, msg: dict) -> None:
        # run_id chỉ biết được sau khi engine tạo run trong DB → lúc đó mới
        # đăng ký session vào registry để client khác attach được.
        if self.run_id is None and msg.get("run_id"):
            self.run_id = msg["run_id"]
            _run_sessions[self.run_id] = self
            self.task_name = msg.get("task_name") or self.task_name
        self.events.append(msg)
        if len(self.events) > _REPLAY_BUFFER_LIMIT:
            del self.events[: len(self.events) - _REPLAY_BUFFER_LIMIT]
        for sub in list(self.subscribers):
            try:
                await sub(msg)
            except Exception:
                self.subscribers.discard(sub)

    async def attach(self, send: Callable[[dict], Awaitable[None]]) -> None:
        """Phát lại lịch sử cho người xem mới rồi cho theo dõi tiếp."""
        for msg in list(self.events):
            try:
                await send(msg)
            except Exception:
                return
        if not self.finished:
            self.subscribers.add(send)

    def detach(self, send: Callable[[dict], Awaitable[None]]) -> None:
        self.subscribers.discard(send)


# run_id -> session (chỉ có sau khi run được tạo trong DB)
_run_sessions: dict[int, _RunSession] = {}
# Giữ tham chiếu mạnh tới task đang chạy — nếu không, asyncio chỉ giữ weak ref
# và task có thể bị garbage collect giữa chừng khiến luồng chạy "biến mất".
_background_runs: set[asyncio.Task] = set()


def _start_background_run(
    task_id: int, triggered_by: str, user_input: str = "", project_id: int | None = None,
) -> _RunSession:
    """Khởi chạy 1 workflow trong nền và trả về session để websocket theo dõi."""
    session = _RunSession(task_id)

    async def _runner() -> None:
        try:
            await _execute_run(
                task_id, triggered_by, session.publish,
                user_input=user_input, project_id=project_id,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Background run cho task %s thất bại", task_id)
            await session.publish({"type": "run_error", "content": str(exc)})
        finally:
            session.finished = True
            session.subscribers.clear()
            if session.run_id is not None:
                asyncio.get_running_loop().call_later(
                    _FINISHED_SESSION_TTL, _run_sessions.pop, session.run_id, None,
                )

    task = asyncio.create_task(_runner())
    session.task = task
    _background_runs.add(task)
    task.add_done_callback(_background_runs.discard)
    return session


def list_active_run_sessions() -> list[dict]:
    return [
        {
            "run_id": s.run_id, "task_id": s.task_id,
            "task_name": s.task_name, "finished": s.finished,
        }
        for s in _run_sessions.values()
    ]


def _meeting_progress_sender(
    meeting_id: int, inner: Callable[[dict], Awaitable[None]],
    node_labels: dict[str, str] | None = None,
) -> Callable[[dict], Awaitable[None]]:
    """Bọc hàm gửi sự kiện của engine để phát tiến độ vào phòng họp.

    Lần chạy nền không có ai nghe WebSocket, nên CEO ngồi trong phòng họp không
    biết quy trình đang ở bước nào hay đã xong chưa. Hàm này dịch sự kiện engine
    thành gói `workflow_progress` gọn để client hiện một bong bóng cập nhật tại chỗ.
    """
    labels = node_labels or {}
    state = {"task_name": "", "total": 0, "step": 0}
    # Một bước hỏng phát ra `agent_error` rồi `run_failed` mang cùng một câu lỗi,
    # nên phòng họp nhận hai tin nhắn giống hệt nhau. Nhớ câu vừa gửi để bỏ trùng.
    last_notice: dict[str, str] = {}

    def _label_of(msg: dict) -> str:
        return (
            msg.get("agent_name")
            or msg.get("tool_name")
            or labels.get(msg.get("node_id") or "")
            or ""
        )

    async def send(msg: dict) -> None:
        await inner(msg)
        kind = msg.get("type")
        progress: dict | None = None

        if kind == "run_started":
            state["task_name"] = msg.get("task_name") or ""
            state["total"] = len(msg.get("steps") or [])
            progress = {"status": "running", "label": "Bắt đầu chạy"}
        elif kind in ("agent_start", "tool_call_start", "node_start", "delay_start"):
            name = _label_of(msg)
            if not name:
                return  # node phụ trợ không có tên gọi được — bỏ qua cho đỡ nhiễu
            state["step"] = msg.get("step") or state["step"] + 1
            progress = {"status": "running", "label": f"{name} đang xử lý"}
        elif kind in ("agent_done", "tool_call_done", "node_done", "delay_done"):
            name = _label_of(msg)
            progress = {"status": "running", "label": f"{name} xong" if name else "Xong một bước"}
        elif kind == "run_paused_for_approval":
            progress = {"status": "waiting", "label": f"Chờ {msg.get('approver') or 'CEO'} duyệt"}
        elif kind == "run_done":
            progress = {"status": "done", "label": "Đã chạy xong"}
        elif kind == "run_cancelled":
            progress = {"status": "cancelled", "label": "Đã huỷ"}
        elif kind in ("run_error", "run_failed", "agent_error", "tool_call_error"):
            progress = {"status": "failed", "label": msg.get("content") or "Thất bại"}

        if not progress:
            return

        payload = {
            "type": "workflow_progress",
            "run_id": msg.get("run_id"),
            "task_name": state["task_name"],
            "step": state["step"],
            "total": state["total"],
            **progress,
        }
        try:
            from api.websocket_meeting import push_meeting_notice, push_meeting_progress
            await push_meeting_progress(meeting_id, payload)
            # Kết quả cuối phải còn lại trong lịch sử họp — bong bóng tiến độ chỉ
            # sống trong phiên đang mở, người vào sau sẽ không thấy gì.
            if progress["status"] in ("done", "failed", "cancelled"):
                text = f'Quy trình "{state["task_name"]}": {progress["label"]}.'
                if last_notice.get("text") != text:
                    last_notice["text"] = text
                    await add_meeting_message(meeting_id, "Hệ thống", "system", text)
                    await push_meeting_notice(meeting_id, text)
        except Exception:
            logger.exception("Không phát được tiến độ vào cuộc họp %s", meeting_id)

    return send


async def _notify_approval_needed(
    *, run_id: int, output_id: int, task_name: str, approver: str,
    project_id: int | None, meeting_id: int | None, preview: str, deadline_note: str,
    images: list[str] | None = None, note: str = "",
) -> None:
    """Báo ra ngoài khi một lần chạy dừng lại chờ duyệt.

    Cần thiết vì lần chạy nền (hẹn giờ / webhook / cuộc họp / nối chuỗi) không có
    client nào nghe WebSocket — không báo thì yêu cầu duyệt nằm im không ai biết.

    Lịch sử vận hành chỉ cần một dòng tóm tắt, nhưng phòng họp thì phải nhận ĐỦ
    nội dung + ảnh: CEO duyệt ngay tại đó nên không được xem bản đã cắt.
    """
    short = preview.strip().replace("\n", " ")
    if len(short) > 180:
        short = short[:180] + "…"
    text = (
        f'Quy trình "{task_name}" đang chờ {approver} duyệt để chạy tiếp'
        f'{deadline_note}. Nội dung: "{short}"' if short else
        f'Quy trình "{task_name}" đang chờ {approver} duyệt để chạy tiếp{deadline_note}.'
    )
    if project_id:
        try:
            await create_ops_history(project_id, output_id, "waiting_review", text, run_id=run_id)
        except Exception:
            logger.exception("Không ghi được ops_history cho yêu cầu duyệt %s", output_id)
    if meeting_id:
        try:
            await add_meeting_message(meeting_id, "Hệ thống", "system", text)
        except Exception:
            logger.exception("Không nhắn được vào cuộc họp %s cho yêu cầu duyệt %s", meeting_id, output_id)
        try:
            # Đẩy thẳng tới CEO nếu đang mở phòng họp — ghi DB thôi thì phải tải
            # lại trang mới thấy, mà lần chạy thì đang đứng chờ. Gói này mang đủ
            # nội dung và ảnh để CEO sửa rồi duyệt ngay trong phòng họp.
            from api.websocket_meeting import push_meeting_progress
            await push_meeting_progress(meeting_id, {
                "type": "approval_request",
                "run_id": run_id,
                "output_id": output_id,
                "task_name": task_name,
                "approver": approver,
                "note": note,
                "content": preview,
                "images": images or [],
                "deadline_note": deadline_note,
            })
        except Exception:
            logger.exception("Không đẩy được thông báo realtime vào cuộc họp %s", meeting_id)
    logger.info("Approval needed: run=%s output=%s approver=%s", run_id, output_id, approver)


def signal_workflow_approval(output_id: int, approved: bool = True, edited_content: str | None = None) -> bool:
    """Resume an in-process approval_gate (CEO duyệt/từ chối) — approved=False khiến
    node approval_gate chạy lại node trước đó thay vì đi tiếp."""
    waiter = _approval_waiters.get(output_id)
    if not waiter:
        return False
    waiter["approved"] = approved
    waiter["edited_content"] = edited_content
    waiter["event"].set()
    return True


def _now() -> str:
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


async def _finish_run(run_id: int, status: str) -> None:
    """Đóng 1 run (completed/failed/cancelled) và đồng bộ ngay dữ liệu cho Xanax
    báo cáo (soul_sync) — không chờ đến lần khởi động server tiếp theo."""
    await update_workflow_run_status(run_id, status, set_completed=True)
    try:
        run = await get_workflow_run(run_id)
        if run and run.get("project_id") and status in ("completed", "failed"):
            label = "hoàn thành" if status == "completed" else "thất bại"
            await create_ops_history(
                run["project_id"], None, f"run_{status}",
                f"Lượt chạy quy trình \"{run.get('task_name') or 'Quy trình'}\" {label}",
                run_id=run_id,
            )
    except Exception:
        pass
    if status in ("completed", "failed"):
        try:
            from core.project_storage import archive_workflow_run
            await archive_workflow_run(run_id)
        except Exception:
            pass
    try:
        from core.soul_sync import sync_soul_md
        asyncio.create_task(sync_soul_md())
    except Exception:
        pass


def _is_error_output(text: str) -> bool:
    stripped = text.strip()
    return any(stripped.startswith(p) for p in _STREAM_ERROR_PREFIXES)


_IMAGE_MARKDOWN_RE = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')


def _strip_image_processing(text: str) -> str:
    """Bỏ khối kỹ thuật IMAGE PROMPT / POSITIVE PROMPT / TỶ LỆ khỏi output của LLM.

    Khối này có thể nằm ngay đầu output (bước tạo ảnh chỉ trả về prompt, không
    kèm caption) — trước đây regex bắt buộc có xuống dòng phía trước nên không
    khớp, khiến toàn bộ prompt lọt vào popup duyệt và vào cả nội dung bài đăng.
    """
    match = re.search(
        r'(?:\A|\n)[ \t]*(?:IMAGE PROMPT|POSITIVE PROMPT)[ \t]*\n',
        text or "", re.IGNORECASE,
    )
    if match:
        return (text[:match.start()]).strip()
    return (text or "").strip()


def _extract_image_markdown(text: str) -> list[str]:
    """Lấy các ảnh đã đính kèm dưới dạng markdown ![...](url)."""
    return _IMAGE_MARKDOWN_RE.findall(text or "")


def _compose_run_result(outputs: list[dict]) -> str:
    """Gộp kết quả của một lần chạy thành nội dung có nghĩa để chuyển tiếp.

    Bước cuối của tác vụ tạo post thường là bước tạo ảnh — nội dung của nó chỉ
    là prompt kỹ thuật + ảnh, không phải bài đăng. Lấy nguyên bước cuối sẽ mất
    caption. Nên ở đây: lấy đoạn văn có nghĩa gần nhất, rồi đính kèm ảnh mới
    nhất tìm được trong cả lần chạy.
    """
    body = ""
    images: list[str] = []
    for out in outputs:
        content = out.get("output_content") or ""
        images.extend(_extract_image_markdown(content))
        text = _IMAGE_MARKDOWN_RE.sub("", _strip_image_processing(content)).strip()
        if text:
            body = text
    if images:
        body = (body + "\n\n" if body else "") + f"![Ảnh đã tạo]({images[-1]})"
    return body


def _estimate_tokens_rough(text: str) -> int:
    """1 token ≈ 4 ký tự — khớp với ước lượng trong core/model_pool_bridge.py."""
    return max(0, len(text or "") // 4)


async def _required_tool_names(skill_ids: list[int]) -> set[str]:
    """Tên các tool mà nhân viên BẮT BUỘC phải gọi thì bước mới tính là xong.

    Chỉ kỹ năng loại 'api'. Người dùng cấu hình hẳn một endpoint rồi giao cho
    nhân viên đúng việc gọi nó — không gọi nghĩa là việc chưa xảy ra, dù nhân
    viên có viết ra bao nhiêu chữ.

    'mcp' và 'builtin' KHÔNG bắt buộc: chúng là công cụ dùng khi cần. Từng đánh
    trượt oan nhân viên tạo ảnh chỉ vì cô ấy có kèm skill cắt ảnh mà lần chạy đó
    không cần cắt — trong khi bài viết và ảnh đều đã giao đủ.
    """
    from core.skill_tools import tool_name_for_skill

    names: set[str] = set()
    for sid in skill_ids or []:
        skill = await get_skill(sid)
        if skill and skill.get("type") == "api":
            names.add(tool_name_for_skill(skill))
    return names


async def _build_agent_tools(skill_ids: list[int]) -> list[dict]:
    """Build OpenAI function schemas for the agent's built-in skills."""
    if not skill_ids:
        return []

    import tools as _registered_tools  # noqa: F401 - ensure registry is populated
    from core.hermes.tool_registry import tool_registry
    from core.mcp_client import sync_mcp_skill_tools, tool_prefix_for_skill
    from core.skill_tools import sync_api_skill_tools, tool_name_for_skill

    # Đồng bộ skill loại 'api' và 'mcp' (cấu hình qua giao diện, không cần code)
    # thành tool thật trong registry trước khi build schema cho agent.
    await sync_api_skill_tools()
    await sync_mcp_skill_tools()

    schemas: list[dict] = []
    seen: set[str] = set()
    for sid in skill_ids:
        skill = await get_skill(sid)
        if not skill:
            continue
        skill_type = skill.get("type")
        if skill_type == "builtin":
            try:
                config = json.loads(skill.get("config_json") or "{}")
            except Exception:
                logger.warning("Skill %s has invalid config_json; skipping built-in tool", sid)
                continue
            tool_names = [config.get("tool_name")] if config.get("tool_name") else []
        elif skill_type == "api":
            tool_names = [tool_name_for_skill(skill)]
        elif skill_type == "mcp":
            # Một MCP server phơi ra nhiều tool, nên 1 skill nở thành N tool.
            prefix = tool_prefix_for_skill(skill)
            tool_names = [t.name for t in tool_registry.list_tools(tag="mcp")
                          if t.name.startswith(prefix)]
            if not tool_names:
                logger.warning(
                    "Skill %s (mcp) chưa có tool nào — MCP server chưa kết nối được?", sid,
                )
        else:
            continue

        for tool_name in tool_names:
            tool = tool_registry.get(tool_name) if tool_name else None
            if not tool:
                logger.warning("Skill %s (%s) references unknown tool %r; skipping", sid, skill_type, tool_name)
                continue
            if tool.name in seen:
                continue
            seen.add(tool.name)
            schema = tool.to_schema()
            schemas.append({
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema["description"],
                    "parameters": schema["parameters"],
                },
            })
    return schemas


async def _maybe_generate_image(
    run_id: int, step_num: int, output_id: int, skill_ids: list[int],
    full_output: str, model_pool_ids: list[int],
    send: Callable[[dict], Awaitable[None]], agent_name: str = "",
) -> str | None:
    """Chạy skill generate_post_image nếu agent có gắn skill này. Trả về None nếu lỗi cứng."""
    has_image_skill = False
    for sid in skill_ids:
        s = await get_skill(sid)
        if s and s.get("name") == "generate_post_image":
            has_image_skill = True
            break

    if not has_image_skill or not full_output:
        return full_output

    from core.image_gen import generate_image, extract_image_prompt, extract_image_ratio, ImageGenError
    from core.project_storage import get_or_create_run_dir
    from core.slugify import slugify

    img_prompt = extract_image_prompt(full_output)
    if not img_prompt:
        return full_output

    ratio = extract_image_ratio(full_output)
    ratio_str = f"{ratio[0]}:{ratio[1]}"

    # Tạo ảnh dùng đúng model đã cấu hình cho nhân viên (tab Nhân sự), không có
    # model riêng cho skill và không phân loại text/ảnh. Luồng ảnh và text dùng
    # chung một helper để giữ nguyên thứ tự ưu tiên, trạng thái và hạn mức ngày.
    from core.model_pool_bridge import CLI_API_STYLES, iter_usable_pool_entries
    from hub.database import (
        record_model_usage,
        record_model_usage_hourly,
        record_model_call_log,
    )

    attempt_errors: list[str] = []
    attempted_any = False
    announced = False
    save_path = None
    skipped_cli: list[str] = []

    for round_index in range(2):
        failed_label: str | None = None
        async for pool_entry in iter_usable_pool_entries(model_pool_ids or []):
            model_label = f"{pool_entry['name']} · {pool_entry['model_id']}"

            api_style = pool_entry.get("api_style") or ""
            # `claude` CLI không sinh được ảnh, và entry CLI cố tình để trống
            # base_url. Không chặn ở đây thì nó ghép thành URL tương đối rồi văng
            # "Request URL is missing an 'http://' or 'https://' protocol", che
            # mất nguyên nhân thật.
            #
            # `codex` CLI thì SINH ĐƯỢC — nó có skill hệ thống `imagegen` chạy
            # bằng gói ChatGPT, nên không cần mua image model riêng.
            if api_style in CLI_API_STYLES and api_style != "codex_cli":
                if model_label not in skipped_cli:
                    skipped_cli.append(model_label)
                continue
            if not announced:
                await send({
                    "type": "agent_chunk",
                    "run_id": run_id,
                    "step": step_num,
                    "content": f"\n\n⏳ Đang tạo ảnh ({ratio_str})...",
                })
                run_dir = await get_or_create_run_dir(run_id)
                agent_slug = slugify(agent_name, fallback=f"buoc-{step_num}")
                save_path = run_dir / f"{step_num:02d}_{agent_slug}.png"
                announced = True
            if failed_label:
                await send({
                    "type": "agent_chunk",
                    "run_id": run_id,
                    "step": step_num,
                    "content": f"\n\n⚠️ {failed_label} lỗi, đang thử {model_label}...",
                })

            attempted_any = True
            usage_state = {"tokens_in": 0, "tokens_out": 0, "tokens_cache": 0}
            try:
                if api_style == "codex_cli":
                    # Codex tự chọn nơi lưu rồi ta copy về; không có usage trả về
                    # nên bảng chi phí ghi 0 cho lượt này — đúng bản chất, ảnh
                    # nằm trong gói thuê bao chứ không tính theo token.
                    from core.cli_provider import generate_image_via_codex
                    await generate_image_via_codex(
                        prompt=img_prompt,
                        save_path=save_path,
                        model_id=pool_entry["model_id"],
                        codex_home=(pool_entry.get("cli_config_dir") or "").strip() or None,
                        ratio=ratio,
                    )
                else:
                    await generate_image(
                        prompt=img_prompt,
                        base_url=pool_entry["base_url"],
                        api_key=pool_entry["api_key"],
                        model=pool_entry["model_id"],
                        save_path=save_path,
                        ratio=ratio,
                        usage_state=usage_state,
                    )
            except ImageGenError as img_err:
                logger.warning(
                    "Tạo ảnh bằng model %s thất bại ở vòng %s: %s",
                    model_label,
                    round_index + 1,
                    img_err,
                )
                attempt_errors.append(f"• {model_label}: {img_err}")
                failed_label = model_label
                continue

            try:
                await record_model_usage(
                    pool_entry["id"],
                    usage_state["tokens_in"],
                    usage_state["tokens_out"],
                    usage_state["tokens_cache"],
                )
                await record_model_usage_hourly(
                    pool_entry["id"],
                    usage_state["tokens_in"],
                    usage_state["tokens_out"],
                    usage_state["tokens_cache"],
                )
                await record_model_call_log(
                    pool_entry["id"],
                    usage_state["tokens_in"],
                    usage_state["tokens_out"],
                    usage_state["tokens_cache"],
                )
            except Exception:
                logger.exception("Không thể ghi usage cho lần tạo ảnh bằng model %s", model_label)

            img_url = f"/api/workflow/runs/{run_id}/archive-file?path={save_path.name}"
            clean_text = _strip_image_processing(full_output)
            full_output = clean_text + f"\n\n![Ảnh đã tạo]({img_url})"
            await send({"type": "agent_image", "run_id": run_id, "step": step_num, "url": img_url})
            return full_output

        if round_index == 0:
            if not attempted_any:
                if skipped_cli:
                    err = (
                        "Nhân viên này chỉ có model không sinh được ảnh ("
                        + ", ".join(skipped_cli)
                        + "). Claude CLI không có khả năng tạo ảnh — hãy gán thêm cho nhân "
                        "viên này một model Codex CLI (dùng skill imagegen của gói ChatGPT, "
                        "không tốn thêm tiền) hoặc một image model qua API."
                    )
                else:
                    err = (
                        "Nhân viên chưa được gán model khả dụng nào. Vui lòng chọn model cho "
                        "nhân viên này ở tab Nhân sự rồi chạy lại."
                    )
                await send({
                    "type": "agent_chunk",
                    "run_id": run_id,
                    "step": step_num,
                    "content": f"\n\n❌ {err}",
                })
                await update_workflow_output(
                    output_id,
                    status="error",
                    output_content=full_output + f"\n\n❌ {err}",
                    review_status="failed",
                    finished_at=_now(),
                )
                await send({
                    "type": "agent_error",
                    "run_id": run_id,
                    "step": step_num,
                    "content": err,
                })
                return None

            await send({
                "type": "agent_chunk",
                "run_id": run_id,
                "step": step_num,
                "content": "\n\n⚠️ Tất cả model đều lỗi, chờ 5 giây rồi thử lại một vòng...",
            })
            await asyncio.sleep(5)

    err = (
        "Tạo ảnh thất bại sau khi thử hết model của nhân viên:\n"
        + "\n".join(attempt_errors)
    )
    if skipped_cli:
        err += (
            "\n\n(Đã bỏ qua model không sinh được ảnh: " + ", ".join(skipped_cli) + ")"
        )
    await send({"type": "agent_chunk", "run_id": run_id, "step": step_num, "content": f"\n\n❌ {err}"})
    await update_workflow_output(
        output_id, status="error", output_content=full_output + f"\n\n❌ {err}",
        review_status="failed", finished_at=_now(),
    )
    await send({"type": "agent_error", "run_id": run_id, "step": step_num, "content": err})
    return None


async def _run_agent_step(
    *, run_id: int, task: dict, node_data: dict, step_num: int, agent_label: str,
    user_input: str, previous_outputs: list[dict[str, Any]],
    send: Callable[[dict], Awaitable[None]], node_id: str | None = None,
    project_id: int | None = None,
) -> dict:
    """Chạy một bước agent (dùng chung cho pipeline tuyến tính và node 'agent' trong graph)."""
    agent_id: int | None = node_data.get("agent_id")
    instructions: str = node_data.get("instructions", "")
    use_rag: bool = bool(node_data.get("use_rag"))

    agent_config = await get_agent_config(agent_id) if agent_id else None
    agent_name: str = agent_config["name"] if agent_config else node_data.get("agent_name", agent_label)
    base_prompt: str = agent_config.get("system_prompt", "") if agent_config else ""

    # Model lấy từ cấu hình nhân viên (tab Nhân sự) theo thứ tự ưu tiên — quy
    # trình không được chọn lại model để tránh rối luồng hoạt động. Nếu model
    # đầu tiên gặp sự cố thì tự động chuyển sang model kế tiếp trong danh sách.
    model_pool_ids: list[int] = []
    if agent_config:
        try:
            model_pool_ids = json.loads(agent_config.get("model_pool_ids_json") or "[]")
        except Exception:
            model_pool_ids = []

    skills_content = ""
    skill_ids: list[int] = []
    if agent_config:
        skill_ids = json.loads(agent_config.get("skills_json") or "[]")
        data_skill_ids = node_data.get("skill_ids")
        if isinstance(data_skill_ids, list) and data_skill_ids:
            selected_skill_ids = {
                int(skill_id) for skill_id in data_skill_ids
                if str(skill_id).isdigit()
            }
            skill_ids = [skill_id for skill_id in skill_ids if skill_id in selected_skill_ids]
        for sid in skill_ids:
            skill = await get_skill(sid)
            if skill:
                content = json.loads(skill.get("config_json") or "{}").get("content", "")
                if content:
                    skills_content += f"\n\n---\n{content}"

    # soul.md riêng của nhân viên (xem core/agent_soul.py) — mô tả/tính cách + dữ liệu
    # thực tế + bài học ĐẠT/KHÔNG ĐẠT từ các lần chạy quy trình trước, để nhân viên tự
    # cải thiện qua từng lần làm việc thay vì lặp lại lỗi cũ.
    soul_content = ""
    if agent_config:
        from core.agent_soul import read_soul, sync_agent_soul
        await sync_agent_soul(agent_config)
        soul_content = read_soul(agent_config["id"])

    system_prompt: str = "\n\n".join(filter(None, [base_prompt, skills_content.strip(), soul_content]))

    output_id = await create_workflow_output(
        run_id=run_id, task_id=task["id"], agent_id=agent_id,
        agent_name=agent_name, step_order=step_num,
    )
    await update_workflow_output(output_id, status="running", review_status="in_progress")
    await send({
        "type": "agent_start", "run_id": run_id, "step": step_num,
        "agent_name": agent_name, "agent_id": agent_id, "output_id": output_id, "node_id": node_id,
    })

    # project_id do lời gọi chạy (manual/schedule/webhook/chain) truyền vào —
    # KHÔNG lấy từ task["project_id"] nữa, để 1 quy trình dùng chung được cho
    # nhiều dự án khác nhau; task["project_id"] giờ chỉ còn là dự án mặc định.
    project_brief = ""
    if project_id:
        project = await get_project(project_id)
        if project and project.get("description"):
            project_brief = project["description"]

    user_content = f"# Dự án: {task['name']}\n"
    if project_brief:
        user_content += f"\n## Bối cảnh dự án\n{project_brief}\n"
    if task.get("description"):
        user_content += f"\n## Mô tả quy trình\n{task['description']}\n"
    if user_input:
        user_content += f"\n## Yêu cầu cụ thể cho lần chạy này\n{user_input}\n"
    if instructions:
        user_content += f"\n## Hướng dẫn riêng cho bước này\n{instructions}\n"

    if use_rag:
        query = " ".join(filter(None, [instructions, task.get("description", ""), user_input]))
        rag_results = await rag_search(query, project_id=project_id)
        rag_ctx = format_rag_context(rag_results)
        if rag_ctx:
            user_content += f"\n{rag_ctx}\n"

    if previous_outputs:
        user_content += "\n---\n## Context from previous steps\n"
        for po in previous_outputs:
            user_content += f"\n### {po['agent_name']} (Step {po['step']}):\n{po['content']}\n"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})

    accumulated: list[str] = []
    from core.skill_tools import (
        begin_api_call_tracking, collect_api_call_failures, collect_tool_invocations,
        end_api_call_tracking,
    )
    api_track_token = begin_api_call_tracking()
    # Đường hermes (không có model pool) không dựng tool, nên để rỗng ở đây —
    # thiếu dòng này là nhánh đó ném NameError ở phép kiểm cuối bước.
    agent_tools: list[dict] = []
    try:
        if model_pool_ids:
            from core.model_pool_bridge import stream_from_agent_models
            agent_tools = await _build_agent_tools(skill_ids)
            try:
                stream_iter = stream_from_agent_models(
                    model_pool_ids, messages, tools=agent_tools or None, skill_ids=skill_ids,
                )
            except Exception as exc:
                await send({"type": "agent_error", "run_id": run_id, "step": step_num, "content": str(exc), "node_id": node_id})
                await update_workflow_output(
                    output_id, status="error", output_content=str(exc),
                    review_status="failed", finished_at=_now(),
                )
                return {"status": "error", "content": str(exc), "output_id": output_id}
        else:
            stream_iter = hermes.stream_with_context(messages)

        async for chunk in stream_iter:
            if _cancel_flags.get(run_id):
                break
            accumulated.append(chunk)
            await send({
                "type": "agent_chunk", "run_id": run_id, "step": step_num,
                "content": chunk, "node_id": node_id,
            })

        full_output = "".join(accumulated)

        if _is_error_output(full_output):
            err_msg = full_output.strip()
            logger.warning("Agent %s returned error content: %s", agent_name, err_msg[:200])
            await update_workflow_output(
                output_id, status="error", output_content=err_msg,
                review_status="failed", finished_at=_now(),
            )
            await send({"type": "agent_error", "run_id": run_id, "step": step_num, "content": err_msg, "node_id": node_id})
            return {"status": "error", "content": err_msg, "output_id": output_id}

        # API thật sự lỗi (token hết hạn, page sai, HTTP 4xx...) thì bước phải
        # trượt — không để model tự diễn giải rồi báo "đã đăng thành công".
        api_failures = collect_api_call_failures()
        if api_failures:
            err_msg = "Gọi API thất bại nên bước này không hoàn tất:\n" + "\n".join(
                f"• {f}" for f in api_failures
            )
            await update_workflow_output(
                output_id, status="error", output_content=full_output + "\n\n❌ " + err_msg,
                review_status="failed", finished_at=_now(),
            )
            await send({"type": "agent_error", "run_id": run_id, "step": step_num, "content": err_msg, "node_id": node_id})
            return {"status": "error", "content": err_msg, "output_id": output_id}

        # Kỹ năng loại 'api' là việc BẮT BUỘC phải làm: người dùng cấu hình hẳn một
        # endpoint và giao cho nhân viên đúng việc gọi nó. Không gọi = việc chưa xảy
        # ra, dù nhân viên có viết ra bao nhiêu chữ.
        #
        # Sự cố thật: nhân viên đăng Facebook chạy trên model không gọi được công cụ.
        # Không một request nào rời khỏi máy, nhưng nhân viên vẫn sinh ra chữ nên bước
        # ghi "Đã chạy xong". Mở fanpage mới biết chưa có bài nào.
        #
        # Kỹ năng 'mcp'/'builtin' thì KHÔNG bắt buộc — chúng là công cụ dùng khi cần.
        # Bắt buộc chúng là đánh trượt oan: nhân viên tạo ảnh có kèm skill cắt ảnh
        # nhưng lần chạy này không cần cắt, vẫn giao đủ bài viết và ảnh.
        required_tools = await _required_tool_names(skill_ids)
        if required_tools and not (required_tools & set(collect_tool_invocations())):
            err_msg = (
                "Nhân viên này có công cụ BẮT BUỘC để thực hiện việc được giao nhưng "
                f"KHÔNG gọi ({', '.join(sorted(required_tools))}), nên việc chưa thật sự "
                "được làm — phần chữ bên dưới chỉ là lời nhân viên tự thuật.\n"
                "Thường do model được gán không hỗ trợ tool-calling. Hãy gán cho nhân "
                "viên này một model kiểu OpenAI-compatible, hoặc một model Claude CLI "
                "(gọi được công cụ qua MCP)."
            )
            await update_workflow_output(
                output_id, status="error", output_content=full_output + "\n\n❌ " + err_msg,
                review_status="failed", finished_at=_now(),
            )
            await send({"type": "agent_error", "run_id": run_id, "step": step_num, "content": err_msg, "node_id": node_id})
            return {"status": "error", "content": err_msg, "output_id": output_id}

        full_output = await _maybe_generate_image(
            run_id, step_num, output_id, skill_ids, full_output, model_pool_ids, send, agent_name,
        )
        if full_output is None:
            return {"status": "error", "content": "image generation failed", "output_id": output_id}

        tokens_in = _estimate_tokens_rough(system_prompt + user_content)
        tokens_out = _estimate_tokens_rough(full_output)
        await update_workflow_output(
            output_id, status="done", output_content=full_output,
            tokens_input=tokens_in, tokens_output=tokens_out,
            review_status="waiting_review", finished_at=_now(),
        )
        await send({"type": "agent_done", "run_id": run_id, "step": step_num, "output_id": output_id, "node_id": node_id})
        return {"status": "done", "content": full_output, "output_id": output_id, "agent_name": agent_name}

    except Exception as exc:
        err = str(exc)
        await update_workflow_output(
            output_id, status="error", output_content=err,
            review_status="failed", finished_at=_now(),
        )
        await send({"type": "agent_error", "run_id": run_id, "step": step_num, "content": err, "node_id": node_id})
        return {"status": "error", "content": err, "output_id": output_id}
    finally:
        end_api_call_tracking(api_track_token)


# ── Chaining: quy trình khác trigger_type='workflow_complete' theo dõi task này ──

async def _chain_downstream(task_id: int, final_output: str) -> None:
    try:
        candidates = await list_workflow_tasks_by_trigger("workflow_complete")
    except Exception:
        return
    for t in candidates:
        try:
            cfg = json.loads(t.get("trigger_config_json") or "{}")
        except Exception:
            cfg = {}
        if cfg.get("source_task_id") == task_id:
            asyncio.create_task(
                execute_workflow_headless(t["id"], user_input=final_output, triggered_by="chained")
            )


# ── Legacy linear pipeline ───────────────────────────────────────────────────

async def _execute_linear_run(
    task: dict, triggered_by: str, send: Callable[[dict], Awaitable[None]], user_input: str = "",
    project_id: int | None = None,
) -> int | None:
    task_id = task["id"]
    # Dự án dùng cho lần chạy này: ưu tiên project_id truyền vào (chạy thủ công
    # chọn dự án khác, hoặc trigger tự động có cấu hình riêng) — nếu không có
    # thì dùng dự án mặc định đã lưu trên task.
    run_project_id = project_id if project_id is not None else task.get("project_id")
    agents_list: list[dict] = []
    try:
        agents_list = sorted(
            json.loads(task.get("agents_json", "[]")),
            key=lambda x: x.get("order", 0),
        )
    except Exception:
        pass

    if not agents_list:
        await send({"type": "error", "content": "Task has no agents configured"})
        return None

    run_id = await create_workflow_run(
        task_id=task_id, project_id=run_project_id,
        task_name=task["name"], triggered_by=triggered_by,
    )
    await update_workflow_run_status(run_id, "running", set_started=True)
    _cancel_flags[run_id] = False

    steps_info = [
        {"step": i + 1, "agent_name": a.get("agent_name", f"Agent {i+1}"), "agent_id": a.get("agent_id")}
        for i, a in enumerate(agents_list)
    ]
    await send({"type": "run_started", "run_id": run_id, "task_name": task["name"], "steps": steps_info})

    previous_outputs: list[dict[str, Any]] = []
    final_output = ""

    try:
        for step_idx, agent_entry in enumerate(agents_list):
            if _cancel_flags.get(run_id):
                await send({"type": "run_cancelled", "run_id": run_id})
                await _finish_run(run_id, "cancelled")
                return run_id

            step_num = step_idx + 1
            result = await _run_agent_step(
                run_id=run_id, task=task, node_data=agent_entry, step_num=step_num,
                agent_label=agent_entry.get("agent_name", f"Agent {step_num}"),
                user_input=user_input, previous_outputs=previous_outputs, send=send,
                project_id=run_project_id,
            )
            if result["status"] == "error":
                await _finish_run(run_id, "failed")
                await send({"type": "run_failed", "run_id": run_id, "content": result.get("content", "")})
                return run_id

            final_output = result["content"]
            previous_outputs.append({
                "agent_name": result.get("agent_name", agent_entry.get("agent_name", "")),
                "step": step_num, "content": final_output,
            })

        await _finish_run(run_id, "completed")
        await send({"type": "run_done", "run_id": run_id})
        await _chain_downstream(task_id, final_output)
        return run_id

    except Exception:
        logger.exception("Workflow run %s failed unexpectedly", run_id)
        await _finish_run(run_id, "failed")
        try:
            await send({"type": "run_error", "run_id": run_id, "content": "Unexpected error"})
        except Exception:
            pass
        return run_id
    finally:
        _cancel_flags.pop(run_id, None)


# ── Graph (n8n-style) pipeline ───────────────────────────────────────────────

async def _execute_graph_run(
    task: dict, graph: dict, triggered_by: str, send: Callable[[dict], Awaitable[None]], user_input: str = "",
    project_id: int | None = None, meeting_id: int | None = None,
) -> int | None:
    task_id = task["id"]
    # Xem giải thích ở _execute_linear_run — project_id truyền vào ghi đè dự án
    # mặc định của task cho riêng lần chạy này.
    run_project_id = project_id if project_id is not None else task.get("project_id")
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])
    if not nodes:
        await send({"type": "error", "content": "Workflow graph rỗng"})
        return None

    outgoing: dict[str, list[dict]] = {}
    incoming: dict[str, list[dict]] = {}
    incoming_count: dict[str, int] = {nid: 0 for nid in nodes}
    for e in edges:
        outgoing.setdefault(e["from"], []).append(e)
        incoming.setdefault(e["to"], []).append(e)
        if e["to"] in incoming_count:
            incoming_count[e["to"]] += 1

    start_nodes = [n for n in nodes.values() if n.get("type") == "trigger"]
    if not start_nodes:
        start_nodes = [n for n in nodes.values() if incoming_count.get(n["id"], 0) == 0]
    if not start_nodes:
        await send({"type": "error", "content": "Không tìm thấy node bắt đầu (trigger)"})
        return None

    run_id = await create_workflow_run(
        task_id=task_id, project_id=run_project_id,
        task_name=task["name"], triggered_by=triggered_by,
    )
    await update_workflow_run_status(run_id, "running", set_started=True)
    _cancel_flags[run_id] = False

    agent_nodes = [n for n in nodes.values() if n.get("type") == "agent"]
    steps_info = [
        {"step": i + 1, "agent_name": n.get("data", {}).get("agent_name") or n["id"], "agent_id": n.get("data", {}).get("agent_id")}
        for i, n in enumerate(agent_nodes)
    ]
    await send({"type": "run_started", "run_id": run_id, "task_name": task["name"], "steps": steps_info})

    from core.project_storage import resolve_workflow_image_path
    initial_image_path = await resolve_workflow_image_path(user_input)
    previous_outputs: list[dict[str, Any]] = []
    state = {
        "last_text": user_input,
        "last_image_path": str(initial_image_path) if initial_image_path else None,
        "final_output": "", "step_counter": 0,
    }
    visited: set[str] = set()

    def input_with_artifacts() -> str:
        text = state["last_text"] or user_input
        if state.get("last_image_path"):
            text += (
                "\n\n---\n## Workflow artifact (system-provided)\n"
                f"Ảnh cần dùng cho bước đăng bài nằm tại file: {state['last_image_path']}\n"
                "Khi gọi công cụ đăng Facebook, truyền chính xác đường dẫn này vào `image_path`; "
                "không đưa dòng metadata này vào caption."
            )
        return text

    async def walk(node_id: str) -> None:
        if node_id in visited or _cancel_flags.get(run_id):
            return  # tránh vòng lặp vô hạn — MVP chưa hỗ trợ loop node
        visited.add(node_id)
        node = nodes.get(node_id)
        if not node:
            return
        ntype = node.get("type")
        data = node.get("data", {}) or {}

        # Báo "đang chạy" cho MỌI loại node (kể cả những loại không có sự kiện
        # *_start riêng như condition/workflow_call/trigger/noop/end) — để UI
        # luôn hiện hiệu ứng viền xoay khi node bắt đầu xử lý, không chỉ với
        # agent/tool_call/delay. Các *_start riêng gửi ngay sau vẫn giữ nguyên,
        # chỉ để cập nhật thêm chi tiết (tên agent/tool...).
        await send({"type": "node_start", "run_id": run_id, "node_id": node_id})

        async def walk_outgoing(edges_to_walk: list[dict] | None = None) -> None:
            branches = edges_to_walk if edges_to_walk is not None else outgoing.get(node_id, [])
            if not branches:
                return
            coroutines = [walk(edge["to"]) for edge in branches]
            if data.get("parallel_out") and len(coroutines) > 1:
                await asyncio.gather(*coroutines)
            else:
                for coroutine in coroutines:
                    await coroutine

        if ntype == "trigger":
            await send({"type": "node_done", "run_id": run_id, "node_id": node_id})
            await walk_outgoing()
            return

        if ntype == "agent":
            state["step_counter"] += 1
            step_num = state["step_counter"]
            from core.skill_tools import reset_workflow_image_path, set_workflow_image_path
            image_token = set_workflow_image_path(state.get("last_image_path"))
            try:
                result = await _run_agent_step(
                    run_id=run_id, task=task, node_data=data, step_num=step_num,
                    agent_label=data.get("agent_name", node_id), user_input=input_with_artifacts(),
                    previous_outputs=previous_outputs, send=send, node_id=node_id,
                    project_id=run_project_id,
                )
            finally:
                reset_workflow_image_path(image_token)
            if result["status"] == "error":
                raise _GraphStepError(result["content"])
            state["last_text"] = result["content"]
            state["final_output"] = state["last_text"]
            previous_outputs.append({
                "agent_name": result.get("agent_name", node_id), "step": step_num, "content": state["last_text"],
            })
            await walk_outgoing()
            return

        if ntype == "condition":
            field = data.get("field", "last_output")
            source_text = state["last_text"] if field == "last_output" else user_input if field == "input" else state.get(field, "")
            mode = data.get("mode", "contains")
            value = (data.get("value") or "").strip()
            haystack = (source_text or "").lower()

            if mode == "not_contains":
                branch_ok = value.lower() not in haystack if value else False
            elif mode == "equals":
                branch_ok = haystack == value.lower()
            elif mode == "regex":
                try:
                    branch_ok = bool(re.search(value, source_text or "", re.IGNORECASE))
                except re.error:
                    branch_ok = False
            else:  # contains
                branch_ok = value.lower() in haystack if value else False

            wanted_branch = "true" if branch_ok else "false"
            await send({"type": "condition_result", "run_id": run_id, "node_id": node_id, "result": branch_ok})
            selected_edges = [
                edge for edge in outgoing.get(node_id, [])
                if edge.get("branch") in (None, "", wanted_branch)
            ]
            await walk_outgoing(selected_edges)
            return

        if ntype == "workflow_call":
            target_id = data.get("target_task_id")
            if target_id:
                # Sub-quy trình được gọi trực tiếp trong cùng 1 lượt chạy — kế thừa
                # đúng dự án của lượt chạy hiện tại (không phải dự án mặc định của
                # sub-task), để cả chuỗi quy trình lồng nhau nhất quán trên 1 dự án.
                # Mặc định CHỜ kết quả (wait=True trừ khi người dùng tắt trong UI) —
                # khớp với kỳ vọng "gọi tác vụ thì lấy được kết quả về", không chạy
                # ngầm âm thầm không rõ kết quả.
                if data.get("wait", True):
                    sub_run_id = await _execute_run(
                        int(target_id), "chained", send,
                        user_input=input_with_artifacts(), project_id=run_project_id,
                    )
                    if sub_run_id:
                        # Tác vụ con hỏng thì quy trình cha phải hỏng theo —
                        # trước đây cha vẫn báo hoàn thành dù tác vụ đăng bài
                        # bên trong đã thất bại.
                        sub_run = await get_workflow_run(sub_run_id)
                        if sub_run and sub_run.get("status") == "failed":
                            message = (
                                f"Tác vụ \"{sub_run.get('task_name') or target_id}\" chạy thất bại "
                                "— quy trình dừng tại đây."
                            )
                            await send({
                                "type": "run_failed", "run_id": run_id,
                                "node_id": node_id, "content": message,
                            })
                            raise _GraphStepError(message, notified=True)
                        sub_outputs = await list_workflow_outputs(sub_run_id)
                        if sub_outputs:
                            state["last_text"] = _compose_run_result(sub_outputs) or state["last_text"]
                            state["final_output"] = state["last_text"]
                            image_path = await resolve_workflow_image_path(state["last_text"])
                            if image_path:
                                state["last_image_path"] = str(image_path)
                else:
                    asyncio.create_task(
                        execute_workflow_headless(int(target_id), user_input=state["last_text"], triggered_by="chained", project_id=run_project_id)
                    )
            await send({"type": "node_done", "run_id": run_id, "node_id": node_id})
            await walk_outgoing()
            return

        if ntype == "tool_call":
            tool_name = str(data.get("tool_name") or "").strip()
            args = data.get("args") if isinstance(data.get("args"), dict) else {}
            await send({
                "type": "tool_call_start", "run_id": run_id,
                "node_id": node_id, "tool_name": tool_name,
            })
            try:
                import tools as _registered_tools  # noqa: F401
                from core.hermes.tool_registry import tool_registry
                from core.mcp_client import sync_mcp_skill_tools
                from core.skill_tools import sync_api_skill_tools
                if not tool_name:
                    raise ValueError("Node công cụ chưa chọn tool_name")
                await sync_api_skill_tools()
                await sync_mcp_skill_tools()
                result = await tool_registry.call(tool_name, args)
                result_text = (
                    result if isinstance(result, str)
                    else json.dumps(result, ensure_ascii=False, default=str)
                )
                state[f"tool_{node_id}"] = result
                state["last_tool_result"] = result
                state["last_text"] = result_text
                state["final_output"] = result_text
                await send({
                    "type": "tool_call_done", "run_id": run_id,
                    "node_id": node_id, "tool_name": tool_name,
                    "result": result_text[:1000],
                })
            except Exception as exc:
                error_text = str(exc)
                state[f"tool_{node_id}_error"] = error_text
                state["last_tool_result"] = {"success": False, "error": error_text}
                await send({
                    "type": "tool_call_error", "run_id": run_id,
                    "node_id": node_id, "tool_name": tool_name, "content": error_text,
                })
            await walk_outgoing()
            return

        if ntype == "set_data":
            assignments = data.get("assignments")
            if isinstance(assignments, dict):
                state.update(assignments)
            await send({
                "type": "data_set", "run_id": run_id, "node_id": node_id,
                "keys": list(assignments) if isinstance(assignments, dict) else [],
            })
            await walk_outgoing()
            return

        if ntype == "delay":
            try:
                seconds = max(0.0, min(float(data.get("seconds") or 0), 300.0))
            except (TypeError, ValueError):
                seconds = 0.0
            await send({
                "type": "delay_start", "run_id": run_id,
                "node_id": node_id, "seconds": seconds,
            })
            if seconds:
                await asyncio.sleep(seconds)
            await send({"type": "delay_done", "run_id": run_id, "node_id": node_id})
            await walk_outgoing()
            return

        if ntype == "stop_error":
            message = str(data.get("message") or "Quy trình bị dừng tại node báo lỗi.")
            await send({
                "type": "run_failed", "run_id": run_id,
                "node_id": node_id, "content": message,
            })
            raise _GraphStepError(message, notified=True)

        if ntype == "approval_gate":
            # Hiện popup nội dung của bước trước cho người duyệt (mặc định "CEO") xem/sửa.
            # Duyệt -> đi tiếp (dùng nội dung đã sửa nếu có). Từ chối -> chạy lại đúng node
            # trước đó (tối đa max_retries lần) rồi hỏi duyệt lại với nội dung mới.
            approver = str(data.get("approver") or "CEO").strip() or "CEO"
            max_retries = int(data.get("max_retries") or 3)
            note = str(data.get("note") or "").strip()
            # Hết hạn chờ duyệt: 0 / bỏ trống = chờ vô hạn (giữ hành vi cũ).
            try:
                timeout_minutes = max(0, int(data.get("timeout_minutes") or 0))
            except (TypeError, ValueError):
                timeout_minutes = 0
            on_timeout = str(data.get("on_timeout") or "fail").strip().lower()
            if on_timeout not in ("fail", "approve", "reject"):
                on_timeout = "fail"
            prev_edges = incoming.get(node_id) or []
            prev_id = prev_edges[0]["from"] if prev_edges else None

            attempt = 0
            while True:
                state["step_counter"] += 1
                output_id = await create_workflow_output(
                    run_id=run_id, task_id=task_id, agent_id=None,
                    agent_name=f"Chờ {approver} duyệt", step_order=state["step_counter"],
                )
                content = state["last_text"] or ""
                # Popup duyệt chỉ hiện KẾT QUẢ: bỏ khối prompt kỹ thuật, tách
                # ảnh ra để client hiện ảnh thật thay vì đường link markdown.
                image_urls = _extract_image_markdown(content)
                review_text = _IMAGE_MARKDOWN_RE.sub("", _strip_image_processing(content)).strip()
                await update_workflow_output(
                    output_id, status="done", output_content=content,
                    review_status="waiting_review", finished_at=_now(),
                )
                waiter = {"event": asyncio.Event(), "approved": None, "edited_content": None}
                _approval_waiters[output_id] = waiter
                await send({
                    "type": "run_paused_for_approval", "run_id": run_id, "node_id": node_id,
                    "output_id": output_id, "content": review_text, "images": image_urls,
                    "note": note, "approver": approver,
                })
                deadline_note = f" (tự xử lý sau {timeout_minutes} phút nếu không ai duyệt)" if timeout_minutes else ""
                await _notify_approval_needed(
                    run_id=run_id, output_id=output_id, task_name=task.get("name") or f"#{task_id}",
                    approver=approver, project_id=run_project_id, meeting_id=meeting_id,
                    preview=review_text, deadline_note=deadline_note,
                    images=image_urls, note=note,
                )
                waited = 0.0
                timed_out = False
                try:
                    while not waiter["event"].is_set() and not _cancel_flags.get(run_id):
                        try:
                            await asyncio.wait_for(waiter["event"].wait(), timeout=_APPROVAL_POLL_SECONDS)
                        except asyncio.TimeoutError:
                            waited += _APPROVAL_POLL_SECONDS
                            if timeout_minutes and waited >= timeout_minutes * 60:
                                timed_out = True
                                break
                finally:
                    _approval_waiters.pop(output_id, None)

                if _cancel_flags.get(run_id):
                    return

                if timed_out:
                    if on_timeout == "fail":
                        message = f"Quá {timeout_minutes} phút không có phản hồi duyệt từ {approver}."
                        await update_workflow_output(output_id, review_status="needs_revision")
                        await send({"type": "run_failed", "run_id": run_id, "node_id": node_id, "content": message})
                        raise _GraphStepError(message, notified=True)
                    # Hết hạn mà vẫn muốn chạy tiếp: coi như đã duyệt / đã từ chối.
                    waiter["approved"] = on_timeout == "approve"
                    logger.info(
                        "Approval timeout run=%s output=%s → %s", run_id, output_id, on_timeout,
                    )

                if waiter["approved"]:
                    edited = waiter["edited_content"]
                    approved_text = review_text if edited is None else edited.strip()
                    for url in image_urls:
                        approved_text += f"\n\n![Ảnh đã tạo]({url})"
                    # Bước sau luôn nhận bản đã duyệt, đã bỏ prompt kỹ thuật.
                    state["last_text"] = approved_text
                    state["final_output"] = approved_text
                    if approved_text != content:
                        await update_workflow_output(output_id, edited_content=approved_text)
                    await send({
                        "type": "approval_resumed", "run_id": run_id,
                        "node_id": node_id, "output_id": output_id,
                    })
                    break

                attempt += 1
                await send({
                    "type": "approval_rejected", "run_id": run_id,
                    "node_id": node_id, "output_id": output_id, "attempt": attempt,
                })
                if not prev_id or attempt >= max_retries:
                    message = (
                        "Không có bước trước đó để chạy lại." if not prev_id
                        else f"Đã bị {approver} từ chối {attempt} lần, vượt quá số lần thử lại tối đa ({max_retries})."
                    )
                    await send({"type": "run_failed", "run_id": run_id, "node_id": node_id, "content": message})
                    raise _GraphStepError(message, notified=True)
                visited.discard(prev_id)
                await walk(prev_id)
                if _cancel_flags.get(run_id):
                    return
                # state["last_text"] giờ là nội dung mới từ lần chạy lại — lặp lại vòng hỏi duyệt

            await walk_outgoing()
            return

        if ntype in {"noop", "end"}:
            await send({"type": "node_done", "run_id": run_id, "node_id": node_id})
            await walk_outgoing()
            return

    try:
        for sn in start_nodes:
            await walk(sn["id"])

        if _cancel_flags.get(run_id):
            await send({"type": "run_cancelled", "run_id": run_id})
            await _finish_run(run_id, "cancelled")
            return run_id

        await _finish_run(run_id, "completed")
        await send({"type": "run_done", "run_id": run_id})
        await _chain_downstream(task_id, state["final_output"])
        return run_id

    except _GraphStepError as step_err:
        await _finish_run(run_id, "failed")
        # Trước đây không gửi sự kiện gì ở đây nên giao diện treo mãi ở trạng
        # thái "đang chạy" dù quy trình đã hỏng.
        if not step_err.notified:
            try:
                await send({
                    "type": "run_failed", "run_id": run_id,
                    "content": str(step_err) or "Quy trình dừng do một bước thất bại.",
                })
            except Exception:
                pass
        return run_id
    except Exception:
        logger.exception("Graph workflow run %s failed unexpectedly", run_id)
        await _finish_run(run_id, "failed")
        try:
            await send({"type": "run_error", "run_id": run_id, "content": "Unexpected error"})
        except Exception:
            pass
        return run_id
    finally:
        _cancel_flags.pop(run_id, None)


# ── Core run engine ───────────────────────────────────────────────────────────

async def _execute_run(
    task_id: int, triggered_by: str, send: Callable[[dict], Awaitable[None]], user_input: str = "",
    project_id: int | None = None, meeting_id: int | None = None,
) -> int | None:
    """Chạy 1 workflow task — tự chọn graph engine hoặc pipeline tuyến tính legacy.

    project_id (tuỳ chọn): dự án dùng cho riêng lần chạy này, ghi đè dự án mặc
    định lưu trên task — cho phép 1 quy trình dùng chung cho nhiều dự án khác
    nhau thay vì gắn cứng vào 1 dự án duy nhất."""
    task = await get_workflow_task(task_id)
    if not task:
        await send({"type": "error", "content": f"Task {task_id} not found"})
        return None

    graph_json = (task.get("graph_json") or "").strip()
    if graph_json:
        try:
            graph = json.loads(graph_json)
            if graph.get("nodes"):
                return await _execute_graph_run(
                    task, graph, triggered_by, send, user_input,
                    project_id=project_id, meeting_id=meeting_id,
                )
        except Exception:
            logger.exception("graph_json không hợp lệ cho task %s, fallback sang pipeline tuyến tính", task_id)

    return await _execute_linear_run(task, triggered_by, send, user_input, project_id=project_id)


async def execute_workflow_headless(
    task_id: int, user_input: str = "", triggered_by: str = "scheduled", project_id: int | None = None,
    meeting_id: int | None = None,
) -> int | None:
    """Run a workflow task without a WebSocket (used by scheduler, webhook, chaining).

    Không có client nào nghe, nên mọi sự kiện chỉ vào log. Riêng node approval_gate
    phải chủ động báo ra ngoài (xem _notify_approval_needed) — nếu không thì lần
    chạy sẽ nằm chờ mà không ai biết. meeting_id (nếu có) là cuộc họp đã kích
    hoạt lần chạy này, dùng để nhắn yêu cầu duyệt ngược lại vào cuộc họp đó và
    phát tiến độ từng bước để CEO thấy đang chạy tới đâu."""
    async def _noop(msg: dict) -> None:
        logger.debug("Headless workflow event: %s", msg.get("type"))

    send = _noop
    if meeting_id:
        # Tên hiển thị của từng node, để báo tiến độ bằng tên bước thay vì node_id
        node_labels: dict[str, str] = {}
        try:
            task_row = await get_workflow_task(task_id)
            graph = json.loads((task_row or {}).get("graph_json") or "{}")
            for node in graph.get("nodes") or []:
                label = (node.get("data") or {}).get("label")
                if label:
                    node_labels[node.get("id")] = label
        except Exception:
            logger.exception("Không đọc được nhãn node của task %s", task_id)
        send = _meeting_progress_sender(meeting_id, _noop, node_labels)

    return await _execute_run(
        task_id, triggered_by, send, user_input=user_input,
        project_id=project_id, meeting_id=meeting_id,
    )


# ── WebSocket handler ─────────────────────────────────────────────────────────

@router.websocket("/ws/workflow")
async def websocket_workflow(ws: WebSocket):
    await ws.accept()

    async def _send(msg: dict) -> None:
        try:
            await ws.send_json(msg)
        except Exception:
            pass

    # Những session mà websocket này đang theo dõi — dùng để gỡ đăng ký khi
    # người dùng đóng tab (run vẫn chạy tiếp, chỉ mất người xem).
    watching: set[_RunSession] = set()

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send({"type": "error", "content": "Invalid JSON"})
                continue

            action = msg.get("action")

            if action == "run":
                task_id = msg.get("task_id")
                if not isinstance(task_id, int):
                    await _send({"type": "error", "content": "task_id (int) required"})
                    continue
                user_input = str(msg.get("input", "")).strip()
                run_project_id = msg.get("project_id")
                if run_project_id is not None and not isinstance(run_project_id, int):
                    run_project_id = None
                session = _start_background_run(
                    task_id, "manual", user_input=user_input, project_id=run_project_id,
                )
                session.subscribers.add(_send)
                watching.add(session)

            elif action == "attach":
                # Người dùng quay lại tab: xem tiếp một lần chạy đang/đã chạy ngầm.
                run_id = msg.get("run_id")
                session = _run_sessions.get(run_id) if isinstance(run_id, int) else None
                if not session:
                    await _send({"type": "attach_failed", "run_id": run_id})
                    continue
                watching.add(session)
                await _send({"type": "attached", "run_id": run_id, "finished": session.finished})
                await session.attach(_send)

            elif action == "list_active":
                await _send({"type": "active_runs", "runs": list_active_run_sessions()})

            elif action == "cancel":
                run_id = msg.get("run_id")
                if isinstance(run_id, int):
                    _cancel_flags[run_id] = True
                    await _send({"type": "cancelling", "run_id": run_id})

            else:
                await _send({"type": "error", "content": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket workflow error")
    finally:
        # Chỉ gỡ người xem — KHÔNG huỷ run. Luồng chạy tiếp tục trong nền.
        for session in watching:
            session.detach(_send)
