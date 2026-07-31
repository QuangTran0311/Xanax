"""Node approval_gate khi chạy nền (hẹn giờ / webhook / cuộc họp).

Không có client WebSocket nào nghe, nên phải kiểm: yêu cầu duyệt có được báo ra
ngoài không, hết hạn có tự xử lý không, và server khởi động lại thì lần chạy treo
được dọn ra sao.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hub import database


def _graph(approval_data: dict) -> str:
    return json.dumps({
        "nodes": [
            {"id": "n1", "type": "trigger", "x": 0, "y": 0, "data": {}},
            {"id": "n2", "type": "set_data", "x": 1, "y": 0,
             "data": {"assignments": {"ghi_chu": "Bai dang thu nghiem"}}},
            {"id": "n3", "type": "approval_gate", "x": 2, "y": 0, "data": approval_data},
        ],
        "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}],
    })


async def _make_task(approval_data: dict, project_id=None) -> int:
    return await database.create_workflow_task(
        name="Quy trinh duyet",
        project_id=project_id,
        graph_json=_graph(approval_data),
        trigger_type="meeting_decision",
    )


async def _wait_for_waiter(wf, timeout: float = 8.0) -> int:
    """Chờ tới khi node duyệt đăng ký waiter, trả về output_id."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if wf._approval_waiters:
            return next(iter(wf._approval_waiters))
        await asyncio.sleep(0.02)
    raise AssertionError("Node duyệt không dừng lại chờ ai cả")


async def test_bao_yeu_cau_duyet_vao_cuoc_hop_va_nhat_ky(tmp_path, monkeypatch):
    """Chạy nền: yêu cầu duyệt phải hiện ở nhật ký dự án VÀ trong cuộc họp."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "a.db"))
    await database.init_db()
    from api import websocket_workflow as wf
    wf._approval_waiters.clear()

    project_id = await database.create_project("Du an A")
    meeting_id = await database.create_meeting("Hop tuan", "chu de", "[]", project_id)
    task_id = await _make_task({"approver": "Quang", "timeout_minutes": 0}, project_id)

    run = asyncio.create_task(wf.execute_workflow_headless(
        task_id, user_input="x", triggered_by="meeting_decision",
        project_id=project_id, meeting_id=meeting_id,
    ))
    output_id = await _wait_for_waiter(wf)

    # Thông báo được gửi ngay sau khi waiter đăng ký → chờ một nhịp cho nó ghi xong
    messages = []
    for _ in range(200):
        messages = await database.get_meeting_messages(meeting_id)
        if messages:
            break
        await asyncio.sleep(0.02)
    assert any("chờ Quang duyệt" in m["content"] for m in messages), messages

    history = await database.list_ops_history(project_id)
    assert any(h["type"] == "waiting_review" for h in history), history

    # Duyệt từ bên ngoài (Hub / API) → lần chạy tiếp tục và kết thúc
    assert wf.signal_workflow_approval(output_id, approved=True) is True
    run_id = await asyncio.wait_for(run, timeout=10)
    assert (await database.get_workflow_run(run_id))["status"] == "completed"


async def test_het_han_cho_duyet_thi_dung_lai(tmp_path, monkeypatch):
    """timeout_minutes + on_timeout='fail' → không treo vô hạn."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "b.db"))
    await database.init_db()
    from api import websocket_workflow as wf
    wf._approval_waiters.clear()
    # 1 phút chờ thật là quá lâu cho test — rút nhịp đếm xuống còn 10ms.
    monkeypatch.setattr(wf, "_APPROVAL_POLL_SECONDS", 0.01)

    project_id = await database.create_project("Du an B")
    task_id = await _make_task(
        {"approver": "Quang", "timeout_minutes": 1, "on_timeout": "fail"}, project_id,
    )

    run_id = await asyncio.wait_for(
        wf.execute_workflow_headless(task_id, triggered_by="scheduled", project_id=project_id),
        timeout=15,
    )
    assert (await database.get_workflow_run(run_id))["status"] == "failed"
    assert not wf._approval_waiters, "waiter phải được dọn khi hết hạn"


async def test_het_han_co_the_tu_duyet_di_tiep(tmp_path, monkeypatch):
    """on_timeout='approve' → hết hạn thì tự duyệt, quy trình chạy tiếp."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "c.db"))
    await database.init_db()
    from api import websocket_workflow as wf
    wf._approval_waiters.clear()
    monkeypatch.setattr(wf, "_APPROVAL_POLL_SECONDS", 0.01)

    project_id = await database.create_project("Du an C")
    task_id = await _make_task(
        {"approver": "Quang", "timeout_minutes": 1, "on_timeout": "approve"}, project_id,
    )

    run_id = await asyncio.wait_for(
        wf.execute_workflow_headless(task_id, triggered_by="webhook", project_id=project_id),
        timeout=15,
    )
    assert (await database.get_workflow_run(run_id))["status"] == "completed"


async def test_don_run_treo_khi_khoi_dong_lai(tmp_path, monkeypatch):
    """Server restart: run 'running' + output 'waiting_review' phải được dọn."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "d.db"))
    await database.init_db()
    from api.routes.workflow import recover_interrupted_runs

    project_id = await database.create_project("Du an D")
    task_id = await _make_task({"approver": "Quang"}, project_id)
    run_id = await database.create_workflow_run(
        task_id=task_id, project_id=project_id, task_name="Quy trinh duyet",
        triggered_by="meeting_decision",
    )
    await database.update_workflow_run_status(run_id, "running")
    output_id = await database.create_workflow_output(
        run_id=run_id, task_id=task_id, agent_id=None, agent_name="Cho Quang duyet", step_order=1,
    )
    await database.update_workflow_output(output_id, review_status="waiting_review")

    await recover_interrupted_runs()

    assert (await database.get_workflow_run(run_id))["status"] == "failed"
    assert (await database.list_workflow_outputs(run_id))[0]["review_status"] == "needs_revision"
