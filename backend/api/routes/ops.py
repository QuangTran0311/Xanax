"""API Routes – Project Ops Dashboard (Overview / Runs / Review Queue / Kanban / History)

Mỗi item hiển thị trên dashboard = 1 workflow_run của cả quy trình. Chi tiết từng
bước/nhân viên AI vẫn được lấy từ workflow_outputs khi cần mở sâu hơn.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hub.database import (
    list_ops_items, get_ops_item, update_workflow_run_review,
    create_ops_history, list_ops_history,
)

router = APIRouter()
logger = logging.getLogger("xanax.routes.ops")

OPS_STATUSES = {
    "pending", "in_progress", "waiting_review", "needs_revision",
    "approved", "completed", "failed", "test",
}
OPS_STATUS_LABELS = {
    "pending": "Chờ xử lý", "in_progress": "Đang thực hiện", "waiting_review": "Chờ CEO duyệt",
    "needs_revision": "Cần chỉnh sửa", "approved": "Đã duyệt", "completed": "Hoàn thành", "failed": "Thất bại",
    "test": "🧪 Test",
}


class FeedbackBody(BaseModel):
    action: str = Field(..., description="'failed' hoặc 'needs_revision'")
    text: str = Field(..., min_length=1)
    is_test: bool = Field(False, description="True = chỉ test quy trình, không ghi lịch sử/bộ nhớ Xanax")


class ApproveBody(BaseModel):
    is_test: bool = Field(False, description="True = chỉ test quy trình, không ghi lịch sử/bộ nhớ Xanax")


class StatusBody(BaseModel):
    status: str


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _display_status(row: dict) -> str:
    run_status = row.get("run_status") or "pending"
    review_status = row.get("review_status") or "waiting_review"
    if run_status in ("pending", "running"):
        return "in_progress"
    if run_status in ("failed", "cancelled"):
        return "failed"
    return review_status


def _shape_item(row: dict) -> dict:
    content = row.get("output_preview") or ""
    summary = (content[:150] + "…") if len(content) > 150 else content
    archive_payload = None
    if row.get("archive_payload_json"):
        import json as _json
        try:
            archive_payload = _json.loads(row["archive_payload_json"])
        except Exception:
            archive_payload = None
    return {
        "id": row["id"],
        "projectId": row["project_id"],
        "workflowId": row["task_id"],
        "workflowName": row.get("workflow_name") or "Quy trình",
        "runStatus": row.get("run_status") or "pending",
        "triggeredBy": row.get("triggered_by") or "manual",
        "outputType": row.get("output_type") or "text",
        "agentId": row.get("agents", [{}])[0].get("agentId") if row.get("agents") else None,
        "agentName": row.get("agents", [{}])[0].get("agentName", "Nhân viên AI") if row.get("agents") else "Nhân viên AI",
        "agentColor": row.get("agents", [{}])[0].get("agentColor") if row.get("agents") else None,
        "agentRole": row.get("agents", [{}])[0].get("agentRole", "") if row.get("agents") else "",
        "agents": row.get("agents") or [],
        "agentCount": row.get("agent_count", 0),
        "outputCount": row.get("output_count", 0),
        "priority": row.get("priority") or "medium",
        "status": _display_status(row),
        "startedAt": row.get("started_at") or row.get("created_at"),
        "finishedAt": row.get("completed_at"),
        "summary": summary or "(chưa có nội dung)",
        "outputPreview": content or "(chưa có nội dung)",
        "feedback": row.get("feedback"),
        "readyForNext": bool(row.get("ready_for_next")),
        "archivePayload": archive_payload,
        "isTest": bool(row.get("last_action_test")),
    }


def _archive_payload(item: dict) -> dict:
    return {
        "workflow": item["workflowName"], "agent": item["agentName"], "status": item["status"],
        "summary": item["summary"], "feedback": item["feedback"], "finishedAt": item["finishedAt"],
    }


async def _compute_ready_for_next(project_id: int, item_id: int, order: int) -> bool:
    """Xác định run vừa duyệt có phải lần chạy sớm nhất còn lại trong hàng chờ không."""
    rows = await list_ops_items(project_id)
    queue = [r for r in rows if _display_status(r) in ("pending", "in_progress", "waiting_review")]
    if not queue:
        return True
    queue.sort(key=lambda r: (r.get("started_at") or r.get("created_at") or "", r["id"]))
    return queue[0]["id"] == item_id


@router.get("/items")
async def get_items(project_id: int):
    rows = await list_ops_items(project_id)
    return {"items": [_shape_item(r) for r in rows]}


@router.get("/history")
async def get_history(project_id: int, limit: int = 200):
    rows = await list_ops_history(project_id, limit)
    return {"history": [
        {"id": r["id"], "ts": r["created_at"], "type": r["type"], "text": r["text"], "runId": r.get("run_id")}
        for r in rows
    ]}


@router.post("/items/{item_id}/approve")
async def approve_item(item_id: int, body: ApproveBody = ApproveBody()):
    row = await get_ops_item(item_id)
    if not row:
        raise HTTPException(404, "Item not found")

    if body.is_test:
        await update_workflow_run_review(item_id, review_status="test", feedback=None, ready_for_next=0, last_action_test=1, reviewed_at=_now())
        return _shape_item({**row, "review_status": "test", "feedback": None, "ready_for_next": 0, "last_action_test": 1})

    ready = await _compute_ready_for_next(row["project_id"], item_id, 0)
    await update_workflow_run_review(
        item_id, review_status="approved", feedback=None, ready_for_next=1 if ready else 0, last_action_test=0, reviewed_at=_now(),
    )
    item = _shape_item({**row, "review_status": "approved", "feedback": None,
                         "ready_for_next": 1 if ready else 0, "last_action_test": 0})
    suffix = " — sẵn sàng chuyển bước tiếp theo" if ready else ""
    await create_ops_history(
        row["project_id"], None, "approved",
        f"CEO duyệt lượt chạy \"{item['workflowName']}\"{suffix}",
        run_id=item_id,
    )
    return item


@router.post("/items/{item_id}/feedback")
async def feedback_item(item_id: int, body: FeedbackBody):
    if body.action not in ("failed", "needs_revision"):
        raise HTTPException(400, "action phải là 'failed' hoặc 'needs_revision'")
    row = await get_ops_item(item_id)
    if not row:
        raise HTTPException(404, "Item not found")
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Vui lòng nhập phản hồi")

    if body.is_test:
        await update_workflow_run_review(item_id, review_status="test", feedback=text, ready_for_next=0, last_action_test=1, reviewed_at=_now())
        return _shape_item({**row, "review_status": "test", "feedback": text, "ready_for_next": 0, "last_action_test": 1})

    kwargs = {"review_status": body.action, "feedback": text, "ready_for_next": 0, "last_action_test": 0}
    item = _shape_item({**row, **{
        "review_status": body.action, "feedback": text, "ready_for_next": 0, "last_action_test": 0,
    }})
    if body.action == "failed":
        import json as _json
        kwargs["archive_payload_json"] = _json.dumps(_archive_payload(item), ensure_ascii=False)
    kwargs["reviewed_at"] = _now()
    await update_workflow_run_review(item_id, **kwargs)

    verb = "đánh dấu KHÔNG ĐẠT" if body.action == "failed" else "yêu cầu chỉnh sửa"
    hist_type = "rejected" if body.action == "failed" else "revision_requested"
    await create_ops_history(
        row["project_id"], None, hist_type,
        f"CEO {verb} lượt chạy \"{item['workflowName']}\" — phản hồi: \"{text}\"",
        run_id=item_id,
    )
    return item


@router.patch("/items/{item_id}")
async def patch_item_status(item_id: int, body: StatusBody):
    """Dùng cho kéo-thả Kanban: cập nhật trực tiếp cột (trạng thái) của 1 item."""
    if body.status not in OPS_STATUSES:
        raise HTTPException(400, f"status không hợp lệ: {body.status}")
    row = await get_ops_item(item_id)
    if not row:
        raise HTTPException(404, "Item not found")
    if row.get("review_status") == body.status:
        return _shape_item(row)

    from_label = OPS_STATUS_LABELS.get(row.get("review_status"), row.get("review_status"))
    kwargs = {"review_status": body.status, "last_action_test": 0}  # kéo-thả tay là hành động thật, không phải test
    if body.status == "approved":
        kwargs["ready_for_next"] = 1 if await _compute_ready_for_next(row["project_id"], item_id, 0) else 0
    else:
        kwargs["ready_for_next"] = 0

    item = _shape_item({**row, **{
        "review_status": body.status, "ready_for_next": kwargs["ready_for_next"], "last_action_test": 0,
    }})
    if body.status in ("completed", "failed"):
        import json as _json
        kwargs["archive_payload_json"] = _json.dumps(_archive_payload(item), ensure_ascii=False)
    kwargs["reviewed_at"] = _now()

    await update_workflow_run_review(item_id, **kwargs)
    await create_ops_history(
        row["project_id"], None, "queue_transition",
        f"Chuyển lượt chạy \"{item['workflowName']}\" từ \"{from_label}\" sang \"{OPS_STATUS_LABELS[body.status]}\"",
        run_id=item_id,
    )
    return item
