"""Cửa hỏi nguồn ảnh: để nhân viên tự vẽ, hay dùng ảnh Papa đưa.

Bật bằng ô `ask_image_source` trên node agent (tab Quy trình). Bước dừng lại hỏi
TRƯỚC khi chạy, vì câu trả lời quyết định bước đó có tốn một lần gọi model sinh
ảnh hay không.

Mọi ngả nghi ngờ đều rơi về hành vi cũ là tự vẽ — hết giờ chờ, ảnh chọn đã bị xoá
khỏi đĩa, hay chọn nhầm id không tồn tại. Cửa này không được phép làm hỏng một
quy trình vốn đang chạy được.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hub import database


def _graph(ask: bool) -> str:
    return json.dumps({
        "nodes": [
            {"id": "n1", "type": "trigger", "x": 0, "y": 0, "data": {}},
            {"id": "n2", "type": "agent", "x": 1, "y": 0,
             "data": {"agent_id": 1, "agent_name": "Lexapro", "ask_image_source": ask}},
        ],
        "edges": [{"from": "n1", "to": "n2"}],
    })


async def _wait_for_gate(wf, timeout: float = 8.0) -> str:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if wf._image_source_waiters:
            return next(iter(wf._image_source_waiters))
        await asyncio.sleep(0.02)
    raise AssertionError("Bước agent không dừng lại hỏi nguồn ảnh")


def _install_fake_agent(wf, monkeypatch, seen: list):
    async def fake_agent_step(**kw):
        seen.append(kw.get("preset_image"))
        output_id = await database.create_workflow_output(
            run_id=kw["run_id"], task_id=kw["task"]["id"], agent_id=None,
            agent_name="Lexapro", step_order=kw["step_num"],
        )
        return {"status": "done", "content": "xong", "output_id": output_id,
                "agent_name": "Lexapro"}

    monkeypatch.setattr(wf, "_run_agent_step", fake_agent_step)


async def test_khong_bat_thi_khong_hoi(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "a.db"))
    await database.init_db()
    from api import websocket_workflow as wf
    wf._image_source_waiters.clear()

    seen: list = []
    _install_fake_agent(wf, monkeypatch, seen)
    task_id = await database.create_workflow_task(
        name="Tao anh", graph_json=_graph(False), trigger_type="manual")

    await asyncio.wait_for(
        wf.execute_workflow_headless(task_id, triggered_by="manual"), timeout=10)
    assert seen == [None]
    assert not wf._image_source_waiters


async def test_chon_anh_co_san_thi_khong_ve_nua(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "b.db"))
    await database.init_db()
    from api import websocket_workflow as wf
    from api.routes import assets as assets_route
    wf._image_source_waiters.clear()

    # Một ảnh nằm sẵn trong tab Tài sản.
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "tui-len.png").write_bytes(b"anh-that")
    monkeypatch.setattr(assets_route, "ASSETS_DIR", assets_dir)
    asset_id = await database.create_asset(
        filename="tui-len.png", stored_path="tui-len.png",
        mime_type="image/png", size_bytes=8, source="upload",
    )

    seen: list = []
    _install_fake_agent(wf, monkeypatch, seen)
    task_id = await database.create_workflow_task(
        name="Tao anh", graph_json=_graph(True), trigger_type="manual")

    run = asyncio.create_task(wf.execute_workflow_headless(task_id, triggered_by="manual"))
    key = await _wait_for_gate(wf)
    run_id, node_id = key.split(":", 1)
    assert wf.signal_image_source(int(run_id), node_id, "asset", asset_id) is True
    await asyncio.wait_for(run, timeout=10)

    assert len(seen) == 1 and seen[0], "bước agent phải nhận được đường dẫn ảnh"
    chosen = Path(seen[0])
    assert chosen.is_file() and chosen.read_bytes() == b"anh-that"
    # Ảnh phải nằm trong thư mục lưu trữ của lần chạy, không phải trỏ ngược về
    # data/assets — thẻ duyệt và bước đăng bài đều lấy file từ thư mục run.
    assert chosen.parent != assets_dir


async def test_anh_da_bi_xoa_thi_quay_ve_tu_ve(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "c.db"))
    await database.init_db()
    from api import websocket_workflow as wf
    from api.routes import assets as assets_route
    wf._image_source_waiters.clear()

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    monkeypatch.setattr(assets_route, "ASSETS_DIR", assets_dir)
    asset_id = await database.create_asset(
        filename="mat-roi.png", stored_path="mat-roi.png",
        mime_type="image/png", size_bytes=0, source="upload",
    )

    seen: list = []
    _install_fake_agent(wf, monkeypatch, seen)
    task_id = await database.create_workflow_task(
        name="Tao anh", graph_json=_graph(True), trigger_type="manual")

    run = asyncio.create_task(wf.execute_workflow_headless(task_id, triggered_by="manual"))
    key = await _wait_for_gate(wf)
    run_id, node_id = key.split(":", 1)
    wf.signal_image_source(int(run_id), node_id, "asset", asset_id)
    await asyncio.wait_for(run, timeout=10)

    assert seen == [None], "file không còn trên đĩa thì phải tự vẽ như cũ, không được dừng quy trình"


async def test_het_gio_cho_thi_tu_ve(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "d.db"))
    await database.init_db()
    from api import websocket_workflow as wf
    wf._image_source_waiters.clear()
    monkeypatch.setattr(wf, "_APPROVAL_POLL_SECONDS", 0.01)
    monkeypatch.setattr(wf, "_IMAGE_SOURCE_TIMEOUT_MINUTES", 0.001)

    seen: list = []
    _install_fake_agent(wf, monkeypatch, seen)
    task_id = await database.create_workflow_task(
        name="Tao anh", graph_json=_graph(True), trigger_type="manual")

    await asyncio.wait_for(
        wf.execute_workflow_headless(task_id, triggered_by="manual"), timeout=15)
    assert seen == [None]
    assert not wf._image_source_waiters, "waiter phải được dọn khi hết giờ"
