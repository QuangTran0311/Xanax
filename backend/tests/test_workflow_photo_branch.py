"""Rẽ nhánh chế độ A/B trong quy trình: người dùng gửi ảnh hay chỉ đưa chủ đề.

Người dùng phổ thông kẹp ảnh sản phẩm vào tin nhắn phòng họp rồi nói muốn gì.
Quy trình phải TỰ nhận ra là có ảnh, tự đi nhánh cắt nền → dựng nền → ghép. Không
kẹp gì thì nhân viên vẽ toàn bộ như trước.

Việc chọn nhánh là chuyện của code, không phải của model: người dùng không biết
"chế độ" là gì và cũng không có cách nào sửa nếu model suy sai.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hub import database

TOOL = "cat_anh_gia"


def _graph() -> str:
    """Đúng hình dạng của tác vụ "Tạo post và ảnh" sau khi sửa."""
    return json.dumps({
        "nodes": [
            {"id": "n1", "type": "trigger", "x": 0, "y": 0, "data": {}},
            {"id": "n2", "type": "agent", "x": 1, "y": 0,
             "data": {"agent_id": 1, "agent_name": "Celexa"}},
            {"id": "n_cond", "type": "condition", "x": 2, "y": 0,
             "data": {"field": "product_image", "mode": "co_du_lieu"}},
            {"id": "n_cut", "type": "tool_call", "x": 3, "y": -1,
             "data": {"tool_name": TOOL, "keep_text": True,
                      "output_state_key": "product_cut_image",
                      "args": {"input_path": "{{product_image}}",
                               "output_path": "{{product_cut_target}}"}}},
            {"id": "n3", "type": "agent", "x": 4, "y": 0,
             "data": {"agent_id": 2, "agent_name": "Lexapro"}},
        ],
        "edges": [
            {"from": "n1", "to": "n2", "branch": None},
            {"from": "n2", "to": "n_cond", "branch": None},
            {"from": "n_cond", "to": "n_cut", "branch": "true"},
            {"from": "n_cond", "to": "n3", "branch": "false"},
            {"from": "n_cut", "to": "n3", "branch": None},
        ],
    })


def _tin_nhan(duong_dan: str) -> str:
    return ("tạo bài đăng từ sản phẩm này\n\n"
            "<!-- FILE PAPA GỬI KÈM — đường dẫn tuyệt đối, dùng cho công cụ:\n"
            f"- dadieu.jpg → {duong_dan}\n-->")


def _lap_dat(wf, monkeypatch, tmp_path, buoc: list, goi_tool: list):
    """Thay nhân viên và công cụ bằng bản giả, giữ nguyên engine thật."""
    async def fake_agent_step(**kw):
        buoc.append({"ten": kw["node_data"].get("agent_name"),
                     "nhan_duoc": kw["user_input"],
                     "anh_san_pham": kw.get("product_image")})
        output_id = await database.create_workflow_output(
            run_id=kw["run_id"], task_id=kw["task"]["id"], agent_id=None,
            agent_name=kw["node_data"].get("agent_name"), step_order=kw["step_num"],
        )
        return {"status": "done", "content": "BÀI POST CELEXA VIẾT",
                "output_id": output_id, "agent_name": kw["node_data"].get("agent_name")}

    monkeypatch.setattr(wf, "_run_agent_step", fake_agent_step)

    # Công cụ giả: ghi ra file thật ở đúng output_path để engine kiểm tra được.
    async def fake_call(name, args):
        goi_tool.append({"ten": name, "args": args})
        Path(args["output_path"]).write_bytes(b"anh-da-cat")
        return f"Đã cắt xong: {args['output_path']}"

    from core.hermes.tool_registry import tool_registry
    monkeypatch.setattr(tool_registry, "call", fake_call)

    async def _noop():
        return None
    monkeypatch.setattr("core.skill_tools.sync_api_skill_tools", _noop)
    monkeypatch.setattr("core.mcp_client.sync_mcp_skill_tools", _noop)

    # data/ giả để safe_product_path chấp nhận đường dẫn trong tmp_path.
    monkeypatch.setattr(wf, "__file__", str(tmp_path / "api" / "x.py"))


async def _chay(wf, tmp_path, monkeypatch, user_input: str):
    buoc: list = []
    goi_tool: list = []
    _lap_dat(wf, monkeypatch, tmp_path, buoc, goi_tool)
    task_id = await database.create_workflow_task(
        name="Tao post va anh", graph_json=_graph(), trigger_type="manual")
    await asyncio.wait_for(
        wf.execute_workflow_headless(task_id, user_input=user_input, triggered_by="manual"),
        timeout=15)
    return buoc, goi_tool


async def test_co_anh_thi_di_nhanh_cat(tmp_path, monkeypatch):
    """Kẹp ảnh vào → node cắt phải chạy, và Lexapro nhận được ảnh đã cắt."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "a.db"))
    await database.init_db()
    from api import websocket_workflow as wf

    data_dir = tmp_path / "api" / ".." / "data" / "assets"
    (tmp_path / "data" / "assets").mkdir(parents=True)
    anh = tmp_path / "data" / "assets" / "abc_dadieu.jpg"
    anh.write_bytes(b"anh-goc")

    buoc, goi_tool = await _chay(wf, tmp_path, monkeypatch, _tin_nhan(str(anh)))

    assert len(goi_tool) == 1, "node cắt ảnh phải chạy đúng một lần"
    assert goi_tool[0]["ten"] == TOOL
    assert goi_tool[0]["args"]["input_path"] == str(anh), "phải nội suy {{product_image}}"
    assert goi_tool[0]["args"]["output_path"].endswith("abc_dadieu_cut.png")

    assert [b["ten"] for b in buoc] == ["Celexa", "Lexapro"]
    # Node cắt KHÔNG được đè mất bài post của Celexa.
    assert "BÀI POST CELEXA VIẾT" in buoc[1]["nhan_duoc"], \
        f"Lexapro nhận nhầm nội dung: {buoc[1]['nhan_duoc'][:120]}"
    assert buoc[1]["anh_san_pham"].endswith("abc_dadieu_cut.png"), \
        "Lexapro phải nhận đường dẫn ảnh ĐÃ CẮT"


async def test_khong_co_anh_thi_bo_qua_node_cat(tmp_path, monkeypatch):
    """Chỉ đưa chủ đề → luồng cũ phải chạy y như trước, không đụng công cụ cắt."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "b.db"))
    await database.init_db()
    from api import websocket_workflow as wf
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)

    buoc, goi_tool = await _chay(wf, tmp_path, monkeypatch, "viết bài giới thiệu shop")

    assert goi_tool == [], "không có ảnh mà vẫn gọi công cụ cắt"
    assert [b["ten"] for b in buoc] == ["Celexa", "Lexapro"]
    assert not buoc[1]["anh_san_pham"], "chế độ A thì không được có ảnh sản phẩm"


def test_noi_suy_tham_so_tu_state():
    """Khoá thiếu phải thành rỗng, đừng để nguyên {{...}} rơi xuống công cụ."""
    from api.websocket_workflow import fill_state_placeholders

    state = {"product_image": r"D:\a\b.jpg", "so": 5}
    assert fill_state_placeholders("{{product_image}}", state) == r"D:\a\b.jpg"
    assert fill_state_placeholders("{{ product_image }}", state) == r"D:\a\b.jpg"
    assert fill_state_placeholders("{{khong_co}}", state) == ""
    assert fill_state_placeholders({"a": ["{{so}}", 7], "b": True}, state) == {"a": ["5", 7], "b": True}
    # Không có dấu ngoặc thì trả nguyên xi — hành vi cũ của node công cụ.
    assert fill_state_placeholders("chuoi thuong", state) == "chuoi thuong"


async def test_cong_cu_chay_hong_thi_khong_ghi_duong_dan(tmp_path, monkeypatch):
    """cut_product báo lỗi bằng CHUỖI chứ không ném exception — "chạy xong"
    không có nghĩa là có file. Ghi bừa đường dẫn thì bước sau đi ghép một file
    không tồn tại."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "d.db"))
    await database.init_db()
    from api import websocket_workflow as wf

    (tmp_path / "data" / "assets").mkdir(parents=True)
    anh = tmp_path / "data" / "assets" / "abc_dadieu.jpg"
    anh.write_bytes(b"anh-goc")

    buoc: list = []
    goi_tool: list = []
    _lap_dat(wf, monkeypatch, tmp_path, buoc, goi_tool)

    # Công cụ "thành công" nhưng không tạo ra file nào.
    async def tool_khong_ra_file(name, args):
        goi_tool.append({"ten": name, "args": args})
        return "Lỗi: không tìm thấy sản phẩm trong ảnh"

    from core.hermes.tool_registry import tool_registry
    monkeypatch.setattr(tool_registry, "call", tool_khong_ra_file)

    task_id = await database.create_workflow_task(
        name="Tao post va anh", graph_json=_graph(), trigger_type="manual")
    await asyncio.wait_for(
        wf.execute_workflow_headless(task_id, user_input=_tin_nhan(str(anh)),
                                     triggered_by="manual"), timeout=15)

    assert len(goi_tool) == 1, "node cắt vẫn phải được gọi"
    assert not buoc[1]["anh_san_pham"], "cắt hỏng mà vẫn đưa đường dẫn cho bước sau"


async def test_bo_qua_duong_dan_ngoai_thu_muc_data(tmp_path, monkeypatch):
    """Chuỗi này đi qua tay model — một đường dẫn bịa không được đem đi cắt."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "c.db"))
    await database.init_db()
    from api import websocket_workflow as wf
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    ngoai = tmp_path / "rieng-tu.jpg"
    ngoai.write_bytes(b"khong-duoc-dung")

    buoc, goi_tool = await _chay(wf, tmp_path, monkeypatch, _tin_nhan(str(ngoai)))

    assert goi_tool == [], "đường dẫn ngoài data/ vẫn lọt vào node cắt"
    assert not buoc[1]["anh_san_pham"]
