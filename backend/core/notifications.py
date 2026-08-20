"""Nguồn dữ liệu và kênh phát chung cho Trung tâm thông báo."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from core.provider_errors import safe_provider_error
from hub.database import (
    get_unread_notification_count,
    get_workflow_run,
    get_workflow_task,
    list_model_pool,
    mark_all_notifications_read,
    mark_notification_read,
    resolve_notification,
    resolve_notifications_for_source,
    upsert_notification,
)

logger = logging.getLogger("xanax.notifications")
SEVERITIES = {"info", "warning", "error"}


def reason_text(reason: str, language: str = "vi") -> str:
    """Ánh xạ mã máy thành câu dành cho người đọc, có fallback an toàn."""
    messages = {
        "no_matching_agent": {
            "vi": "Không tìm thấy nhân viên AI phù hợp với công việc này.",
            "en": "No suitable AI employee was found for this work item.",
        },
    }
    translated = messages.get(reason, {})
    return translated.get(language) or translated.get("vi") or reason.replace("_", " ").strip()


def public_notification(notification: dict) -> dict:
    result = dict(notification)
    raw_payload = result.pop("payload_json", "{}")
    try:
        payload = json.loads(raw_payload or "{}")
    except (TypeError, json.JSONDecodeError):
        payload = {}
    result["payload"] = payload if isinstance(payload, dict) else {}
    return result


class NotificationManager:
    """Fan-out không chặn nguồn phát; snapshot luôn dựng lại được từ SQLite."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def broadcast(self, event: dict) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass


notification_manager = NotificationManager()


async def _broadcast_change(event_type: str, notification: dict | None = None, **extra) -> None:
    event = {
        "type": event_type,
        "unread_count": await get_unread_notification_count(),
        **extra,
    }
    if notification is not None:
        event["notification"] = public_notification(notification)
    await notification_manager.broadcast(event)


async def create_notification(
    *, kind: str, severity: str, title: str, body: str = "",
    payload: dict[str, Any] | None = None, link: str = "",
    source_type: str = "", source_id: str | int = "",
) -> dict:
    if severity not in SEVERITIES:
        raise ValueError(f"Unsupported notification severity: {severity}")
    notification, created = await upsert_notification(
        kind=kind,
        severity=severity,
        title=title.strip() or kind,
        body=body.strip(),
        payload_json=json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":")),
        link=link if link.startswith("/hub") else "",
        source_type=source_type.strip(),
        source_id=str(source_id),
    )
    await _broadcast_change(
        "notification.created" if created else "notification.updated", notification,
    )
    return public_notification(notification)


async def read_notification(notification_id: int) -> dict | None:
    notification = await mark_notification_read(notification_id)
    if notification:
        await _broadcast_change("notification.updated", notification)
        return public_notification(notification)
    return None


async def read_all_notifications() -> int:
    changed = await mark_all_notifications_read()
    await _broadcast_change("notifications.read_all", changed=changed)
    return changed


async def resolve_one_notification(notification_id: int) -> dict | None:
    notification = await resolve_notification(notification_id)
    if notification:
        await _broadcast_change("notification.updated", notification)
        return public_notification(notification)
    return None


async def resolve_source_notifications(source_type: str, source_id: str | int) -> int:
    notifications = await resolve_notifications_for_source(source_type, str(source_id))
    for notification in notifications:
        await _broadcast_change("notification.updated", notification)
    return len(notifications)


async def notify_workflow_run_failed(run_id: int) -> None:
    run = await get_workflow_run(run_id)
    if not run:
        return
    task_id = int(run.get("task_id") or 0)
    task = await get_workflow_task(task_id) if task_id else None
    tab = "company-runner" if (task or {}).get("kind") == "company" else "auto-runner"
    name = str(run.get("task_name") or (task or {}).get("name") or f"Workflow #{run_id}")
    await create_notification(
        kind="workflow_failed",
        severity="error",
        title=f"Workflow failed: {name}",
        body="The workflow run stopped with a failed status. Open it to inspect the run details.",
        payload={"run_id": run_id, "task_id": task_id, "task_name": name},
        link=f"/hub/{tab}/{task_id}?attachRun={run_id}" if task_id else f"/hub/{tab}",
        source_type="workflow_run",
        source_id=run_id,
    )


async def notify_experiment_finished(
    experiment_id: int, name: str, status: str, *, judge_error_count: int = 0,
) -> None:
    has_judge_errors = judge_error_count > 0
    await create_notification(
        kind="experiment_judge_error" if has_judge_errors else "experiment_completed",
        severity="warning" if has_judge_errors else ("error" if status == "failed" else "info"),
        title=f"Experiment finished: {name}",
        body=(
            f"The experiment finished with {judge_error_count} judge error(s)."
            if has_judge_errors
            else f"The experiment finished with status {status}."
        ),
        payload={
            "experiment_id": experiment_id,
            "status": status,
            "judge_error_count": judge_error_count,
        },
        link=f"/hub/model?experiment={experiment_id}",
        source_type="experiment",
        source_id=experiment_id,
    )


async def check_cli_auth_notifications() -> None:
    """Kiểm tra định kỳ auth CLI bằng đúng probe dùng bởi endpoint model-pool."""
    from core.cli_login import read_cli_auth_status

    entries = await list_model_pool(enabled_only=True)
    for entry in entries:
        if entry.get("api_style") not in {"claude_cli", "codex_cli"}:
            continue
        entry_id = int(entry["id"])
        try:
            status = await read_cli_auth_status(entry)
            if status.get("logged_in") is True:
                await resolve_source_notifications("model_pool_auth", entry_id)
                continue
            diagnostic = "CLI authentication is no longer active. Sign in again to use this model."
            severity = "warning"
        except Exception as exc:
            diagnostic = safe_provider_error(exc, entry)
            severity = "error"
            logger.warning(
                "CLI auth notification probe failed for model pool %s (%s)",
                entry_id, type(exc).__name__,
            )
        await create_notification(
            kind="model_pool_auth_failed",
            severity=severity,
            title=f"CLI sign-in required: {entry.get('name') or entry.get('model_id') or entry_id}",
            body=diagnostic,
            payload={
                "model_pool_id": entry_id,
                "api_style": entry.get("api_style"),
                "model_name": entry.get("name") or "",
            },
            link=f"/hub/model?model={entry_id}",
            source_type="model_pool_auth",
            source_id=entry_id,
        )
