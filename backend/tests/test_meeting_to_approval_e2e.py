"""CEO nói trong phòng họp → quy trình chạy thật → dừng ở cổng duyệt và báo ngược lại.

Test này gọi execute_workflow_headless THẬT (không mock) để bắt lỗi lệch chữ ký
giữa phòng họp và engine — thứ mà test dùng hàm giả không phát hiện được.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hub import database


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_json(self, payload):
        self.sent.append(payload)


GRAPH = {
    "nodes": [
        {"id": "n1", "type": "trigger", "x": 0, "y": 0, "data": {}},
        {"id": "n2", "type": "set_data", "x": 1, "y": 0,
         "data": {"label": "Soạn nội dung", "assignments": {"noi_dung": "bài về móc khóa"}}},
        {"id": "n3", "type": "approval_gate", "x": 2, "y": 0,
         "data": {"label": "Duyệt", "approver": "CEO"}},
        {"id": "n4", "type": "end", "x": 3, "y": 0, "data": {}},
    ],
    "edges": [
        {"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"},
    ],
}


async def test_goi_tu_phong_hop_chay_that_va_bao_khi_cho_duyet(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "e2e.db"))
    await database.init_db()
    from api import websocket_meeting as wm

    project_id = await database.create_project("Fanpage")
    meeting_id = await database.create_meeting("Hop tuan", "", "[]", project_id)
    task_id = await database.create_workflow_task(
        name="Dang bai len fanpage", project_id=project_id, kind="company",
        graph_json=json.dumps(GRAPH),
    )
    await database.update_workflow_task(task_id, status="active")

    ws = FakeWS()
    notes = await wm._run_workflows_from_meeting(
        meeting_id, project_id, [{"task_id": task_id, "input": "móc khóa hình mèo"}],
    )
    assert "quy trình" in notes[0]

    # Chờ engine chạy tới cổng duyệt (nó sẽ nằm chờ ở đó)
    for _ in range(60):
        await asyncio.sleep(0.05)
        messages = await database.get_meeting_messages(meeting_id)
        if any("chờ CEO duyệt" in m["content"] for m in messages):
            break
    else:
        raise AssertionError(
            "Không có tin nhắn báo chờ duyệt trong phòng họp sau 3s. "
            f"Đang có: {[m['content'] for m in await database.get_meeting_messages(meeting_id)]}"
        )

    # Lần chạy phải tồn tại thật, gắn đúng dự án, và ghi nhận nguồn kích hoạt
    runs = await database.list_workflow_runs(task_id=task_id)
    assert runs, "quy trình không hề chạy — nhiều khả năng lệch chữ ký hàm"
    assert runs[0]["triggered_by"] == "meeting_chat"
    assert runs[0]["project_id"] == project_id

    # Yêu cầu duyệt phải nằm trong hàng chờ của đúng dự án đó
    items = await database.list_ops_items(project_id)
    assert items, "yêu cầu duyệt không xuất hiện trong hàng chờ của dự án"

    # Dọn dẹp: huỷ lần chạy đang treo ở cổng duyệt để test không để lại task nền
    from api.websocket_workflow import _cancel_flags
    _cancel_flags[runs[0]["id"]] = True
    await asyncio.sleep(0.2)


async def test_ceo_dang_mo_phong_hop_thay_thong_bao_ngay(tmp_path, monkeypatch):
    """Không chỉ ghi DB — phải đẩy tới client đang mở phòng họp."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "live.db"))
    await database.init_db()
    from api import websocket_meeting as wm

    project_id = await database.create_project("Fanpage")
    meeting_id = await database.create_meeting("Hop tuan", "", "[]", project_id)
    task_id = await database.create_workflow_task(
        name="Dang bai len fanpage", project_id=project_id, kind="company",
        graph_json=json.dumps(GRAPH),
    )
    await database.update_workflow_task(task_id, status="active")

    # Giả lập CEO đang mở phòng họp
    received = []

    async def fake_send(payload):
        received.append(payload)

    wm._meeting_clients.setdefault(meeting_id, set()).add(fake_send)
    try:
        await wm._run_workflows_from_meeting(
            meeting_id, project_id, [{"task_id": task_id, "input": "móc khóa"}],
        )
        for _ in range(60):
            await asyncio.sleep(0.05)
            if any(p.get("type") == "approval_request" for p in received):
                break
        else:
            raise AssertionError(f"CEO không nhận được thẻ duyệt realtime. Nhận: {received}")

        card = next(p for p in received if p["type"] == "approval_request")
        assert card["approver"] == "CEO"
        assert card["output_id"]

        # Vẫn phải có mốc "đang chờ duyệt" trong tiến độ để bong bóng đổi trạng thái
        assert any(p.get("status") == "waiting" for p in received if p.get("type") == "workflow_progress")
    finally:
        wm._meeting_clients.get(meeting_id, set()).discard(fake_send)
        runs = await database.list_workflow_runs(task_id=task_id)
        from api.websocket_workflow import _cancel_flags
        for r in runs:
            _cancel_flags[r["id"]] = True
        await asyncio.sleep(0.2)


async def test_tien_do_tung_buoc_hien_trong_phong_hop(tmp_path, monkeypatch):
    """CEO phải thấy đang chạy bước nào và khi nào xong, không chỉ lúc chờ duyệt."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "prog.db"))
    await database.init_db()
    from api import websocket_meeting as wm

    project_id = await database.create_project("Fanpage")
    meeting_id = await database.create_meeting("Hop", "", "[]", project_id)
    graph = {
        "nodes": [
            {"id": "n1", "type": "trigger", "x": 0, "y": 0, "data": {}},
            {"id": "n2", "type": "set_data", "x": 1, "y": 0,
             "data": {"label": "Soạn nội dung", "assignments": {"a": "1"}}},
            {"id": "n3", "type": "delay", "x": 2, "y": 0, "data": {"label": "Chờ chút", "seconds": 0}},
            {"id": "n4", "type": "end", "x": 3, "y": 0, "data": {}},
        ],
        "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}],
    }
    task_id = await database.create_workflow_task(
        name="Quy trinh test", project_id=project_id, kind="company",
        graph_json=json.dumps(graph),
    )
    await database.update_workflow_task(task_id, status="active")

    received = []

    async def fake_send(payload):
        received.append(payload)

    wm._meeting_clients.setdefault(meeting_id, set()).add(fake_send)
    try:
        await wm._run_workflows_from_meeting(
            meeting_id, project_id, [{"task_id": task_id, "input": "chủ đề"}],
        )
        for _ in range(80):
            await asyncio.sleep(0.05)
            if any(p.get("type") == "workflow_progress" and p.get("status") == "done" for p in received):
                break
        else:
            raise AssertionError(f"Không thấy tiến độ chạy xong. Nhận: {received}")

        progress = [p for p in received if p.get("type") == "workflow_progress"]
        assert progress[0]["status"] == "running"
        assert progress[0]["task_name"] == "Quy trinh test"
        # Tên bước thật, không phải node_id
        assert any("Soạn nội dung" in p["label"] for p in progress), progress
        assert progress[-1]["status"] == "done"

        # Mốc cuối phải còn lại trong lịch sử họp cho người vào sau
        messages = await database.get_meeting_messages(meeting_id)
        assert any("Đã chạy xong" in m["content"] for m in messages)
    finally:
        wm._meeting_clients.get(meeting_id, set()).discard(fake_send)


async def test_yeu_cau_duyet_gui_du_noi_dung_va_anh(tmp_path, monkeypatch):
    """CEO duyệt ngay trong phòng họp nên phải nhận ĐỦ nội dung, không phải bản cắt."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "rich.db"))
    await database.init_db()
    from api import websocket_meeting as wm
    import api.websocket_workflow as wf

    meeting_id = await database.create_meeting("Hop", "", "[]", None)
    received = []

    async def fake_send(payload):
        received.append(payload)

    wm._meeting_clients.setdefault(meeting_id, set()).add(fake_send)
    try:
        long_text = "Bài đăng rất dài. " * 40          # > 180 ký tự
        await wf._notify_approval_needed(
            run_id=1, output_id=7, task_name="Đăng bài", approver="CEO",
            project_id=None, meeting_id=meeting_id,
            preview=long_text, deadline_note="", images=["/api/anh1.png"], note="xem kỹ ảnh",
        )
    finally:
        wm._meeting_clients.get(meeting_id, set()).discard(fake_send)

    card = next(p for p in received if p.get("type") == "approval_request")
    assert card["content"] == long_text, "nội dung bị cắt — CEO không sửa được bản đầy đủ"
    assert card["images"] == ["/api/anh1.png"]
    assert card["output_id"] == 7 and card["approver"] == "CEO"
    assert card["note"] == "xem kỹ ảnh"

    # Dòng lưu vào lịch sử họp vẫn là bản tóm tắt ngắn, không nhét cả bài vào
    messages = await database.get_meeting_messages(meeting_id)
    assert any("đang chờ CEO duyệt" in m["content"] for m in messages)
    assert all(len(m["content"]) < 400 for m in messages)
