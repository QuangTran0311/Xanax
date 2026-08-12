"""Bấm "Không duyệt" ở cổng duyệt phải DẠY được, không chỉ chạy lại.

Hai thứ được kiểm ở đây, vì thiếu một trong hai thì vòng lặp "chê → sửa" vẫn hỏng:

1. Lần chạy lại nhận đúng đề bài cũ kèm lý do bị chê — trước đây nó nhận chính bài
   vừa bị chê làm đề bài, nên nhân viên trả ra bản gần y hệt.
2. Lời chê ở lại trong soul nhân viên, để lần chạy sau (buổi khác, quy trình khác)
   vẫn còn nhớ.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hub import database


def _graph() -> str:
    return json.dumps({
        "nodes": [
            {"id": "n1", "type": "trigger", "x": 0, "y": 0, "data": {}},
            {"id": "n2", "type": "agent", "x": 1, "y": 0,
             "data": {"agent_id": 1, "agent_name": "Celexa"}},
            {"id": "n3", "type": "approval_gate", "x": 2, "y": 0,
             "data": {"approver": "Papa", "max_retries": 3}},
        ],
        "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}],
    })


async def _wait_for_waiter(wf, exclude: set[int], timeout: float = 8.0) -> int:
    """Chờ một cửa duyệt MỚI mở ra (bỏ qua các cửa đã xử lý ở vòng trước)."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        fresh = set(wf._approval_waiters) - exclude
        if fresh:
            return next(iter(fresh))
        await asyncio.sleep(0.02)
    raise AssertionError("Cổng duyệt không mở ra cửa nào")


async def test_tu_choi_thi_viet_lai_theo_de_bai_cu_va_ghi_vao_soul(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "a.db"))
    await database.init_db()

    from api import websocket_workflow as wf
    from core import agent_soul
    monkeypatch.setattr(agent_soul, "SOULS_DIR", tmp_path / "souls")
    wf._approval_waiters.clear()

    agent_id = await database.create_agent_config(name="Celexa", role="Content Creator")
    task_id = await database.create_workflow_task(
        name="Tao post", graph_json=_graph(), trigger_type="manual",
    )

    # Nhân viên giả: ghi lại đề bài đã nhận, trả ra một bài đăng khác nhau mỗi lần
    # để phân biệt được bản đầu với bản viết lại.
    briefs: list[str] = []

    async def fake_agent_step(**kw):
        briefs.append(kw["user_input"])
        output_id = await database.create_workflow_output(
            run_id=kw["run_id"], task_id=kw["task"]["id"], agent_id=agent_id,
            agent_name="Celexa", step_order=kw["step_num"],
        )
        content = f"Ban thu {len(briefs)}"
        await database.update_workflow_output(output_id, output_content=content, status="done")
        return {"status": "done", "content": content,
                "output_id": output_id, "agent_name": "Celexa"}

    monkeypatch.setattr(wf, "_run_agent_step", fake_agent_step)

    run = asyncio.create_task(wf.execute_workflow_headless(
        task_id, user_input="tui xach bang len", triggered_by="manual",
    ))

    first_gate = await _wait_for_waiter(wf, exclude=set())
    assert wf.signal_workflow_approval(
        first_gate, approved=False, notes="liet ke cong dung nhu quang cao",
    ) is True

    second_gate = await _wait_for_waiter(wf, exclude={first_gate})
    assert wf.signal_workflow_approval(second_gate, approved=True) is True
    run_id = await asyncio.wait_for(run, timeout=10)
    assert (await database.get_workflow_run(run_id))["status"] == "completed"

    # 1. Lần viết lại phải quay về đề bài gốc, KHÔNG lấy bản bị chê làm đề bài,
    #    và phải đọc được lý do.
    assert len(briefs) == 2, briefs
    assert "tui xach bang len" in briefs[1]
    assert "liet ke cong dung nhu quang cao" in briefs[1]
    assert "Ban thu 1" not in briefs[1]

    # 2. Lời chê ở lại trong soul của đúng nhân viên đã viết bản bị chê.
    soul = agent_soul.read_soul(agent_id)
    assert "KHÔNG ĐẠT" in soul
    assert "liet ke cong dung nhu quang cao" in soul
    assert "Ban thu 1" in soul


async def test_duyet_thi_ghi_bai_mau_vao_soul_du_an(tmp_path, monkeypatch):
    """Bấm Duyệt phải để lại bài mẫu — nếu không thì soul chỉ toàn điều cấm."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "c.db"))
    await database.init_db()

    from api import websocket_workflow as wf
    from core import project_soul
    monkeypatch.setattr(project_soul, "PROJECT_SOULS_DIR", tmp_path / "projects")
    wf._approval_waiters.clear()

    project_id = await database.create_project("Fanpage len")
    agent_id = await database.create_agent_config(name="Celexa")
    task_id = await database.create_workflow_task(
        name="Tao post", project_id=project_id, graph_json=_graph(), trigger_type="manual",
    )

    author_outputs: list[int] = []

    async def fake_agent_step(**kw):
        output_id = await database.create_workflow_output(
            run_id=kw["run_id"], task_id=kw["task"]["id"], agent_id=agent_id,
            agent_name="Celexa", step_order=kw["step_num"],
        )
        author_outputs.append(output_id)
        content = "Ban may viet ra"
        await database.update_workflow_output(output_id, output_content=content, status="done")
        return {"status": "done", "content": content,
                "output_id": output_id, "agent_name": "Celexa"}

    monkeypatch.setattr(wf, "_run_agent_step", fake_agent_step)

    run = asyncio.create_task(wf.execute_workflow_headless(
        task_id, user_input="moc khoa co 4 la", triggered_by="manual", project_id=project_id,
    ))
    gate = await _wait_for_waiter(wf, exclude=set())
    # Papa sửa tay trước khi duyệt — cặp trước/sau phải được giữ lại.
    assert wf.signal_workflow_approval(
        gate, approved=True, edited_content="Ban Papa sua tay roi duyet",
    ) is True
    await asyncio.wait_for(run, timeout=10)

    soul = project_soul.read_project_soul(project_id)
    assert "Ban Papa sua tay roi duyet" in soul
    assert "Ban may viet ra" in soul, "phải giữ cả bản gốc để thấy Papa đã sửa gì"
    assert "SỬA TAY" in soul

    # Lần chạy của nhân viên được đánh dấu đạt, nhưng KHÔNG chép lại nguyên bài vào
    # soul nhân viên — chép hai chỗ là bài đăng nằm hai lần trong mỗi prompt.
    out = await database.get_workflow_output(author_outputs[-1])
    assert out["pass_fail"] == "pass", out


async def test_chi_giu_lai_vai_bai_mau_gan_nhat(tmp_path, monkeypatch):
    """Bài mẫu đi vào prompt của MỌI lần chạy — giữ hết là soul dự án phình vô hạn."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "d.db"))
    await database.init_db()
    from core import project_soul
    monkeypatch.setattr(project_soul, "PROJECT_SOULS_DIR", tmp_path / "projects")

    project_id = await database.create_project("Fanpage len")
    for i in range(project_soul._MAX_APPROVED + 2):
        project_soul.append_approved_example(project_id, "Fanpage len", f"Bai so {i}")

    soul = project_soul.read_project_soul(project_id)
    assert "Bai so 0" not in soul, "bài cũ nhất phải bị đẩy ra"
    assert f"Bai so {project_soul._MAX_APPROVED + 1}" in soul
    assert soul.count("[Đã duyệt]") == project_soul._MAX_APPROVED


async def test_tu_choi_khong_kem_ly_do_thi_khong_ghi_soul(tmp_path, monkeypatch):
    """Một mục "KHÔNG ĐẠT" trơ trọi không dạy được gì — thà đừng ghi còn hơn làm
    soul phình ra bằng những dòng nhân viên đọc xong vẫn phải đoán."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "b.db"))
    await database.init_db()

    from api import websocket_workflow as wf
    from core import agent_soul
    monkeypatch.setattr(agent_soul, "SOULS_DIR", tmp_path / "souls")

    agent_id = await database.create_agent_config(name="Celexa", role="Content Creator")
    await wf._record_rejection(
        author={"agent_id": agent_id, "agent_name": "Celexa", "output_id": None},
        reason="", review_text="Ban thu 1", task_name="Tao post", approver="Papa",
    )
    assert "KHÔNG ĐẠT" not in agent_soul.read_soul(agent_id)
