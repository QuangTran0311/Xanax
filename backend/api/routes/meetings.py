"""API Routes – Meeting management CRUD"""
import asyncio
import json
import logging
import re
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from hub.database import (
    list_meetings, get_meeting, create_meeting, update_meeting, delete_meeting,
    get_meeting_messages, get_recent_meeting_messages, finalize_meeting,
    list_workflow_tasks_by_trigger, get_all_agents_with_skills, create_work_item,
)
from core.matcher import match_agent_for_task

router = APIRouter()
logger = logging.getLogger("xanax.routes.meetings")


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1)
    topic: str = Field("")
    participants: list[int] = Field(default_factory=list)
    project_id: int | None = None


class MeetingUpdate(BaseModel):
    title: str | None = None
    topic: str | None = None
    participants: list[int] | None = None
    status: str | None = None


class MeetingFinalize(BaseModel):
    decision_text: str = Field(..., min_length=1)


class ProposedItemApproval(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field("")
    priority: str = Field("medium")
    assigned_agent_id: int | None = None
    include: bool = True


class MeetingItemsApproval(BaseModel):
    items: list[ProposedItemApproval] = Field(default_factory=list)


def _parse_json_list(raw: str) -> list[dict]:
    """Parse the first JSON array in an LLM response, including fenced output."""
    text = (raw or "").strip()
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\[", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _fallback_work_items(decision_text: str) -> list[dict]:
    """Conservative fallback when the model does not return valid JSON."""
    items: list[dict] = []
    for line in (decision_text or "").splitlines():
        clean = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if clean == line.strip() or len(clean) < 4:
            continue
        title = clean.split(":", 1)[0].strip()[:160]
        description = clean if clean != title else ""
        items.append({"title": title, "description": description, "priority": "medium"})
        if len(items) >= 12:
            break
    return items


async def _extract_work_items_from_decision(
    decision_text: str,
    draft_minutes: str,
) -> list[dict]:
    """Ask Xanax to turn finalized minutes into concise, trackable work items."""
    from core.hermes_bridge import hermes

    prompt = (
        "Bạn là Xanax. Từ BIÊN BẢN ĐÃ CHỐT bên dưới, hãy tách CHỈ những hành động "
        "cụ thể cần theo dõi thành danh sách công việc. Không biến nội dung thảo luận "
        "hoặc quyết định thuần thông tin thành công việc. Trả về DUY NHẤT một JSON array, "
        "không markdown, theo schema: "
        '[{"title":"...", "description":"...", "priority":"low|medium|high"}]. '
        "Tiêu đề ngắn gọn, mô tả đủ bối cảnh để nhân viên thực hiện. Tối đa 12 mục.\n\n"
        f"BIÊN BẢN NHÁP (ngữ cảnh):\n{draft_minutes or '(không có)'}\n\n"
        f"BIÊN BẢN ĐÃ CHỐT:\n{decision_text}"
    )
    try:
        raw = await hermes.complete_with_context([
            {"role": "system", "content": "Bạn là trợ lý điều hành, xuất JSON hợp lệ."},
            {"role": "user", "content": prompt},
        ])
        parsed = _parse_json_list(raw)
    except Exception:
        logger.exception("Could not extract work items from finalized meeting")
        parsed = []

    source = parsed or _fallback_work_items(decision_text)
    normalized: list[dict] = []
    for item in source[:12]:
        title = str(item.get("title") or "").strip()[:200]
        if not title:
            continue
        priority = str(item.get("priority") or "medium").lower()
        if priority not in {"low", "medium", "high"}:
            priority = "medium"
        normalized.append({
            "title": title,
            "description": str(item.get("description") or "").strip(),
            "priority": priority,
        })
    return normalized


def _parse(m: dict) -> dict:
    m["participants"] = json.loads(m.get("participants_json", "[]"))
    try:
        m["proposed_items"] = json.loads(m.get("proposed_items_json", "[]"))
    except (TypeError, json.JSONDecodeError):
        m["proposed_items"] = []
    return m


@router.get("/")
async def list_all_meetings():
    meetings = await list_meetings()
    return {"meetings": [_parse(m) for m in meetings]}


@router.post("/", status_code=201)
async def create_new_meeting(body: MeetingCreate):
    meeting_id = await create_meeting(
        title=body.title,
        topic=body.topic,
        participants_json=json.dumps(body.participants),
        project_id=body.project_id,
    )
    m = await get_meeting(meeting_id)
    return _parse(m)


@router.get("/messages/recent")
async def get_recent_messages(limit: int = Query(8, ge=1, le=50)):
    return {"rooms": await get_recent_meeting_messages(limit)}


@router.get("/{meeting_id}")
async def get_one_meeting(meeting_id: int):
    m = await get_meeting(meeting_id)
    if not m:
        raise HTTPException(404, "Meeting not found")
    return _parse(m)


@router.patch("/{meeting_id}")
async def patch_meeting(meeting_id: int, body: MeetingUpdate):
    kwargs = {}
    data = body.model_dump()
    for k in ("title", "topic", "status"):
        if data.get(k) is not None:
            kwargs[k] = data[k]
    if data.get("participants") is not None:
        kwargs["participants_json"] = json.dumps(data["participants"])
    ok = await update_meeting(meeting_id, **kwargs)
    if not ok:
        raise HTTPException(404, "Meeting not found")
    m = await get_meeting(meeting_id)
    return _parse(m)


@router.delete("/{meeting_id}", status_code=204)
async def remove_meeting(meeting_id: int):
    ok = await delete_meeting(meeting_id)
    if not ok:
        raise HTTPException(404, "Meeting not found")


@router.post("/{meeting_id}/finalize")
async def finalize_meeting_decision(meeting_id: int, body: MeetingFinalize):
    """Chốt kế hoạch cuộc họp. Đây là điểm duy nhất cấp quyền cho Xanax tự động
    trigger các quy trình (workflow_tasks) đã gắn trigger_type='meeting_decision'
    cho đúng dự án — Xanax không được tự ý ra lệnh khi chưa chốt."""
    m = await get_meeting(meeting_id)
    if not m:
        raise HTTPException(404, "Meeting not found")

    ok = await finalize_meeting(meeting_id, body.decision_text)
    if not ok:
        raise HTTPException(404, "Meeting not found")
    m = await get_meeting(meeting_id)

    proposed_items: list[dict] = []
    if m.get("project_id") is not None:
        extracted = await _extract_work_items_from_decision(
            body.decision_text,
            m.get("draft_minutes") or "",
        )
        agents = await get_all_agents_with_skills()
        for item in extracted:
            match = match_agent_for_task(item["title"], item["description"], agents)
            best = match.best
            proposed_items.append({
                **item,
                "suggested_agent_id": best.agent_id if best else None,
                "suggested_agent_name": best.agent_name if best else "",
                "match_reason": best.reason if best else "",
            })
        await update_meeting(
            meeting_id,
            proposed_items_json=json.dumps(proposed_items, ensure_ascii=False),
        )
        m = await get_meeting(meeting_id)

    triggered: list[int] = []
    candidates = await list_workflow_tasks_by_trigger("meeting_decision")
    for task in candidates:
        try:
            cfg = json.loads(task.get("trigger_config_json") or "{}")
        except Exception:
            cfg = {}
        linked_project = cfg.get("project_id")
        linked_meeting = cfg.get("meeting_id")
        matches = (linked_meeting == meeting_id) or (
            linked_project is not None and linked_project == m.get("project_id")
        )
        if not matches:
            continue
        from api.websocket_workflow import execute_workflow_headless
        # Truyền dự án của chính cuộc họp (không để run rơi về dự án mặc định của
        # task, vì như vậy yêu cầu duyệt sẽ nằm sai hàng chờ hoặc không thuộc dự
        # án nào) và meeting_id để node duyệt nhắn ngược lại đúng cuộc họp này.
        asyncio.create_task(execute_workflow_headless(
            task["id"], user_input=body.decision_text, triggered_by="meeting_decision",
            project_id=m.get("project_id"), meeting_id=meeting_id,
        ))
        triggered.append(task["id"])

    # Đồng bộ ngay để Xanax báo cáo được quyết định vừa chốt mà không cần restart server
    from core.soul_sync import sync_soul_md
    asyncio.create_task(sync_soul_md())

    return {**_parse(m), "triggered_workflow_ids": triggered}


@router.post("/{meeting_id}/approve-items")
async def approve_meeting_items(meeting_id: int, body: MeetingItemsApproval):
    """Create only the CEO-approved proposals in the meeting's linked project."""
    m = await get_meeting(meeting_id)
    if not m:
        raise HTTPException(404, "Meeting not found")
    if m.get("project_id") is None:
        raise HTTPException(400, "Meeting is not linked to a project")
    try:
        pending_items = json.loads(m.get("proposed_items_json") or "[]")
    except (TypeError, json.JSONDecodeError):
        pending_items = []
    if not pending_items:
        raise HTTPException(409, "Meeting has no pending work item proposals")

    valid_priorities = {"low", "medium", "high"}
    agent_ids = {agent["id"] for agent in await get_all_agents_with_skills()}
    created_ids: list[int] = []
    for item in body.items:
        if not item.include:
            continue
        priority = item.priority.lower()
        if priority not in valid_priorities:
            priority = "medium"
        assigned_agent_id = (
            item.assigned_agent_id if item.assigned_agent_id in agent_ids else None
        )
        item_id = await create_work_item(
            project_id=m["project_id"],
            title=item.title.strip(),
            description=item.description.strip(),
            priority=priority,
            assigned_agent_id=assigned_agent_id,
        )
        created_ids.append(item_id)

    await update_meeting(meeting_id, proposed_items_json="[]")
    return {"work_item_ids": created_ids, "project_id": m["project_id"]}


@router.get("/{meeting_id}/messages")
async def get_messages(meeting_id: int):
    m = await get_meeting(meeting_id)
    if not m:
        raise HTTPException(404, "Meeting not found")
    return {"messages": await get_meeting_messages(meeting_id)}
