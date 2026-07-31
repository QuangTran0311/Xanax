"""Xanax kích hoạt quy trình từ phòng họp.

Trước đây phòng họp không có đường nào chạy quy trình (chỉ chat huấn luyện mới
có [[XANAX:trigger_workflow]]), nên Xanax trả lời CEO là "không có trigger".
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hub import database


class FakeWS:
    """Ghi lại các gói tin gửi về client thay vì mở websocket thật."""

    def __init__(self):
        self.sent = []

    async def send_json(self, payload):
        self.sent.append(payload)


def test_parse_run_workflows_tu_json_cua_xanax():
    from api.websocket_meeting import _parse_orchestrator_json

    decision = _parse_orchestrator_json(json.dumps({
        "reply": "Con chạy ngay ạ.",
        "call_agents": [],
        "dismiss_agents": [],
        "run_workflows": [{"task_id": "14", "input": "lót ly len hoa cúc"}],
    }, ensure_ascii=False))
    assert decision["run_workflows"] == [{"task_id": 14, "input": "lót ly len hoa cúc"}]


def test_json_cu_khong_co_run_workflows_van_chay_duoc():
    """Model trả JSON theo format cũ → không được vỡ, chỉ là không chạy quy trình nào."""
    from api.websocket_meeting import _parse_orchestrator_json

    decision = _parse_orchestrator_json('{"reply":"ok","call_agents":[],"dismiss_agents":[]}')
    assert decision["run_workflows"] == []

    fallback = _parse_orchestrator_json("không phải JSON")
    assert fallback["run_workflows"] == []
    assert fallback["reply"] == "không phải JSON"


async def test_chay_quy_trinh_kem_chu_de_tu_phong_hop(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "a.db"))
    await database.init_db()
    from api import websocket_meeting as wm

    project_id = await database.create_project("Fanpage")
    meeting_id = await database.create_meeting("Hop", "", "[]", project_id)
    task_id = await database.create_workflow_task(
        name="Dang bai len fanpage", project_id=project_id, kind="company",
    )
    await database.update_workflow_task(task_id, status="active")

    called = {}

    async def fake_headless(task_id, user_input="", triggered_by="scheduled", project_id=None, meeting_id=None):
        called.update(task_id=task_id, user_input=user_input, triggered_by=triggered_by,
                      project_id=project_id, meeting_id=meeting_id)

    import api.websocket_workflow as wf
    monkeypatch.setattr(wf, "execute_workflow_headless", fake_headless)

    ws = FakeWS()
    notes = await wm._run_workflows_from_meeting(
        ws, meeting_id, project_id, [{"task_id": task_id, "input": "móc khóa hình thú"}],
    )
    await asyncio.sleep(0.05)  # để asyncio.create_task chạy

    assert called["task_id"] == task_id
    assert called["user_input"] == "móc khóa hình thú"      # chủ đề đi kèm, không rỗng
    assert called["project_id"] == project_id
    assert called["meeting_id"] == meeting_id               # để node duyệt nhắn ngược lại
    assert "móc khóa hình thú" in notes[0]

    # Xanax phải nói ra trong phòng họp là đã chạy, và lời đó được lưu vào lịch sử họp
    assert any(p.get("type") == "agent_chunk" for p in ws.sent)
    messages = await database.get_meeting_messages(meeting_id)
    assert any("Đã kích hoạt quy trình" in m["content"] for m in messages)


async def test_khong_chay_quy_trinh_dang_tat(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "b.db"))
    await database.init_db()
    from api import websocket_meeting as wm

    project_id = await database.create_project("Fanpage")
    meeting_id = await database.create_meeting("Hop", "", "[]", project_id)
    task_id = await database.create_workflow_task(name="Quy trinh nhap", project_id=project_id)
    await database.update_workflow_task(task_id, status="paused")  # đang tắt → không được chạy

    ran = []

    async def fake_headless(*args, **kwargs):
        ran.append(kwargs)

    import api.websocket_workflow as wf
    monkeypatch.setattr(wf, "execute_workflow_headless", fake_headless)

    notes = await wm._run_workflows_from_meeting(
        FakeWS(), meeting_id, project_id, [{"task_id": task_id, "input": "x"}],
    )
    await asyncio.sleep(0.05)
    assert not ran, "quy trình chưa bật thì không được chạy"
    assert "đang tắt" in notes[0]


async def test_bao_khi_khong_tim_thay_quy_trinh(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "c.db"))
    await database.init_db()
    from api import websocket_meeting as wm

    meeting_id = await database.create_meeting("Hop", "", "[]", None)
    notes = await wm._run_workflows_from_meeting(
        FakeWS(), meeting_id, None, [{"task_id": 999, "input": "x"}],
    )
    assert "Không tìm thấy quy trình/tác vụ #999" in notes[0]


async def test_phan_biet_quy_trinh_va_tac_vu(tmp_path, monkeypatch):
    """Danh sách đưa cho Xanax phải tách 2 nhóm, và câu xác nhận gọi đúng tên loại."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "d.db"))
    await database.init_db()
    from api import websocket_meeting as wm

    project_id = await database.create_project("Fanpage")
    meeting_id = await database.create_meeting("Hop", "", "[]", project_id)
    quy_trinh = await database.create_workflow_task(
        name="Dang bai len fanpage", project_id=project_id, kind="company",
    )
    tac_vu = await database.create_workflow_task(
        name="Dang bai len fanpage", project_id=project_id, kind="automation",
    )

    roster = await wm._build_workflow_roster_text()
    assert "QUY TRÌNH" in roster and "TÁC VỤ" in roster
    quy_trinh_block, tac_vu_block = roster.split("TÁC VỤ")
    assert f"id={quy_trinh}" in quy_trinh_block, roster
    assert f"id={tac_vu}" in tac_vu_block, roster

    async def fake_headless(*args, **kwargs):
        pass

    import api.websocket_workflow as wf
    monkeypatch.setattr(wf, "execute_workflow_headless", fake_headless)

    notes = await wm._run_workflows_from_meeting(
        FakeWS(), meeting_id, project_id, [{"task_id": quy_trinh, "input": "x"}],
    )
    assert 'Đã kích hoạt quy trình' in notes[0], notes

    notes = await wm._run_workflows_from_meeting(
        FakeWS(), meeting_id, project_id, [{"task_id": tac_vu, "input": "x"}],
    )
    assert 'Đã kích hoạt tác vụ' in notes[0], notes
