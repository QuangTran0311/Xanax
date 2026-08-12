"""Phòng dạy phải thử được nhân viên và kỹ năng, không chỉ nói chuyện suông.

Hai thứ được kiểm:
- Học viên đọc được NỘI DUNG KỸ NĂNG của chính mình khi vào lớp. Thiếu nó thì buổi
  dạy về một kỹ năng diễn ra mà học viên chưa từng thấy mô tả kỹ năng đó.
- Học viên có kỹ năng tạo ảnh mà viết ra IMAGE PROMPT thì ảnh được vẽ THẬT ngay
  trong buổi học, để Papa chê tại chỗ thay vì phải chạy cả quy trình mới biết.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hub import database


class _FakeWS:
    """Chỉ cần đủ cho `_send`: nó gửi bằng send_text và chỉ gửi khi còn CONNECTED."""
    def __init__(self):
        from fastapi.websockets import WebSocketState
        self.sent: list[dict] = []
        self.client_state = WebSocketState.CONNECTED

    async def send_text(self, raw: str):
        self.sent.append(json.loads(raw))


async def _make_agent_with_image_skill() -> tuple[int, dict]:
    skill_id = await database.create_skill(
        name="generate_post_image", description="",
        type_="custom", config_json=json.dumps({"content": "# generate_post_image\nKhuôn IMAGE PROMPT"}),
    )
    agent_id = await database.create_agent_config(
        name="Lexapro", role="Designer", system_prompt="Bạn là Lexapro.",
        skills_json=json.dumps([skill_id]), model_pool_ids_json="[1]",
    )
    return skill_id, await database.get_agent_config(agent_id)


async def test_hoc_vien_doc_duoc_noi_dung_ky_nang(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "a.db"))
    await database.init_db()
    _, agent = await _make_agent_with_image_skill()

    from api.websocket_meeting import _build_skills_content
    content = await _build_skills_content(agent)
    assert "Khuôn IMAGE PROMPT" in content, \
        "phòng dạy ghép nội dung kỹ năng bằng đúng hàm này — hỏng ở đây là hỏng cả lớp"


async def test_ve_that_khi_hoc_vien_viet_image_prompt(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "b.db"))
    await database.init_db()
    _, agent = await _make_agent_with_image_skill()

    from api import websocket_training as wt
    monkeypatch.setattr(wt, "TRAINING_IMAGE_DIR", tmp_path / "training-images")

    drawn = {}

    async def fake_generate(*, prompt, ratio, model_pool_ids, save_path, notify=None,
                            product_overlay=None, placement=None):
        drawn.update(prompt=prompt, ratio=ratio, path=save_path, overlay=product_overlay,
                     placement=placement)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(b"anh")
        return None

    monkeypatch.setattr("core.image_gen.generate_with_agent_models", fake_generate)

    ws = _FakeWS()
    reply = "Dạ con làm thử.\n\nIMAGE PROMPT\nA cozy crochet flat lay\n\nTỶ LỆ\n4:5"
    out = await wt._maybe_draw_in_class(ws, agent, 7, reply, [1])

    assert drawn["prompt"].startswith("A cozy crochet flat lay")
    assert drawn["ratio"] == (4, 5)
    assert drawn["path"].parent.name == "7", "ảnh phải nằm trong thư mục của đúng buổi học"
    assert "/api/training/sessions/7/image/" in out
    assert any("![Ảnh vẽ thử]" in (m.get("content") or "") for m in ws.sent)
    assert drawn["placement"] is None, "không khai báo VỊ TRÍ SẢN PHẨM thì để mặc định"


async def test_hoc_vien_tu_chon_vi_tri_san_pham(tmp_path, monkeypatch):
    """Khối VỊ TRÍ SẢN PHẨM phải đi được từ lời học viên tới lúc ghép ảnh."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "e.db"))
    await database.init_db()
    _, agent = await _make_agent_with_image_skill()

    from api import websocket_training as wt
    monkeypatch.setattr(wt, "TRAINING_IMAGE_DIR", tmp_path / "training-images")

    drawn = {}

    async def fake_generate(*, prompt, ratio, model_pool_ids, save_path, notify=None,
                            product_overlay=None, placement=None):
        drawn["placement"] = placement
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(b"anh")
        return None

    monkeypatch.setattr("core.image_gen.generate_with_agent_models", fake_generate)

    reply = ("IMAGE PROMPT\nan empty cream backdrop\n\nTỶ LỆ\n4:5\n\n"
             "VỊ TRÍ SẢN PHẨM\ncao: 0.78\nxuống: 0.02")
    await wt._maybe_draw_in_class(_FakeWS(), agent, 7, reply, [1])
    assert drawn["placement"] == (0.78, 0.02)


async def test_ve_hong_thi_buoi_hoc_van_chay_tiep(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "c.db"))
    await database.init_db()
    _, agent = await _make_agent_with_image_skill()

    from api import websocket_training as wt
    monkeypatch.setattr(wt, "TRAINING_IMAGE_DIR", tmp_path / "training-images")

    async def fake_generate(**kw):
        return "model nào cũng lỗi"

    monkeypatch.setattr("core.image_gen.generate_with_agent_models", fake_generate)

    ws = _FakeWS()
    out = await wt._maybe_draw_in_class(
        ws, agent, 7, "IMAGE PROMPT\nmot cai gi do\n\nTỶ LỆ\n4:5", [1])
    assert "Vẽ thử không thành" in out
    assert "mot cai gi do" in out, "câu trả lời của học viên phải còn nguyên"


async def test_khong_co_ky_nang_anh_thi_khong_ve(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "d.db"))
    await database.init_db()
    agent_id = await database.create_agent_config(name="Celexa", skills_json="[]")
    agent = await database.get_agent_config(agent_id)

    from api import websocket_training as wt

    async def boom(**kw):
        raise AssertionError("không được gọi tới bộ sinh ảnh")

    monkeypatch.setattr("core.image_gen.generate_with_agent_models", boom)

    ws = _FakeWS()
    text = "IMAGE PROMPT\nabc\n\nTỶ LỆ\n4:5"
    assert await wt._maybe_draw_in_class(ws, agent, 7, text, [1]) == text


# ── Cấp công cụ thật cho học viên, theo từng buổi ──────────────────────────

async def test_mac_dinh_hoc_vien_khong_co_cong_cu(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "e.db"))
    await database.init_db()
    _, agent = await _make_agent_with_image_skill()

    from api import websocket_training as wt
    assert await wt._student_tools(agent, []) == []


async def test_chi_cap_dung_cong_cu_da_tick(tmp_path, monkeypatch):
    """Tick một công cụ thì các công cụ khác của cùng nhân viên vẫn phải bị khoá."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "f.db"))
    await database.init_db()

    from core.hermes.tool_registry import ToolDefinition, tool_registry
    from api import websocket_training as wt

    # Hai skill 'builtin': một cái cắt ảnh (vô hại), một cái đăng bài (nguy hiểm).
    for name in ("cut_anh_thu", "dang_bai_thu"):
        tool_registry.register_tool(ToolDefinition(
            name=name, description=name, parameters=[], handler=lambda: None, tags=[]))
    cut_id = await database.create_skill(
        name="cat_anh", type_="builtin", config_json=json.dumps({"tool_name": "cut_anh_thu"}))
    post_id = await database.create_skill(
        name="dang_bai", type_="builtin", config_json=json.dumps({"tool_name": "dang_bai_thu"}))
    agent_id = await database.create_agent_config(
        name="Lexapro", skills_json=json.dumps([cut_id, post_id]))
    agent = await database.get_agent_config(agent_id)

    granted = await wt._student_tools(agent, ["cut_anh_thu"])
    assert [s["function"]["name"] for s in granted] == ["cut_anh_thu"], \
        "công cụ đăng bài không được lọt vào buổi dạy chỉ cho phép cắt ảnh"

    # Đường CLI nhận công cụ qua skill_ids chứ không qua tools[] — phải thu hẹp theo.
    kept, _ = await wt._student_skill_scope(agent, {"cut_anh_thu"})
    assert kept == [cut_id]


async def test_khong_goi_duoc_tool_ngoai_danh_sach_da_cap(monkeypatch):
    """Registry là kho CHUNG của cả hệ thống.

    Model nêu tên một tool không nằm trong `tools[]` đã gửi lên thì phải bị từ
    chối, chứ không phải cứ có trong registry là chạy. Không có hàng rào này thì
    buổi dạy chỉ cấp `cut_product` vẫn gọi được công cụ đăng bài thật.
    """
    from core import model_pool_bridge as mpb
    from core.hermes.tool_registry import ToolDefinition, tool_registry

    called: list[int] = []
    tool_registry.register_tool(ToolDefinition(
        name="tool_bi_cam", description="", parameters=[],
        handler=lambda **kw: called.append(1), tags=[]))
    tool_registry.register_tool(ToolDefinition(
        name="tool_duoc_cap", description="", parameters=[],
        handler=lambda **kw: "ok", tags=[]))

    rounds: list[dict] = []

    class _FakeResponse:
        def __init__(self, lines): self._lines = lines
        def raise_for_status(self): pass
        async def aiter_lines(self):
            for line in self._lines:
                yield line

    class _FakeStream:
        def __init__(self, lines): self._lines = lines
        async def __aenter__(self): return _FakeResponse(self._lines)
        async def __aexit__(self, *exc): return False

    class _FakeClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *exc): return False

        def stream(self, method, url, headers=None, json=None):
            rounds.append(json)
            if len(rounds) == 1:
                call = {"index": 0, "id": "c1",
                        "function": {"name": "tool_bi_cam", "arguments": "{}"}}
                return _FakeStream([
                    'data: ' + _json.dumps({"choices": [{"delta": {"tool_calls": [call]}}]}),
                    'data: [DONE]',
                ])
            return _FakeStream([
                'data: ' + _json.dumps({"choices": [{"delta": {"content": "xong"}}]}),
                'data: [DONE]',
            ])

    import json as _json
    monkeypatch.setattr(mpb.httpx, "AsyncClient", _FakeClient)

    tools = [{"type": "function", "function": {"name": "tool_duoc_cap",
                                               "description": "", "parameters": {}}}]
    out = ""
    async for chunk in mpb._stream_openai(
        "http://x", "k", "m", [{"role": "user", "content": "hi"}],
        {"tokens_in": 0, "tokens_out": 0, "tokens_cache": 0}, tools,
    ):
        out += chunk

    assert called == [], "tool ngoài danh sách được cấp mà vẫn chạy"
    # Lỗi phải quay lại cho model dưới dạng message tool, để nó biết mà đổi hướng.
    follow_up = rounds[1]["messages"]
    denial = [m for m in follow_up if m.get("role") == "tool"][0]
    assert "không được cấp công cụ" in denial["content"]
    assert out == "xong"


async def test_luu_va_doc_lai_duoc_cong_cu_da_cap(tmp_path, monkeypatch):
    """Vòng lưu → đọc lại phải kín.

    Ca thật đã dính: `get_training_session` liệt kê cột tường minh, thêm cột mới
    vào bảng mà quên thêm vào câu SELECT thì nơi dùng luôn đọc ra None — tick bao
    nhiêu công cụ cũng vô nghĩa, mà không có lỗi nào báo ra.
    """
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "g.db"))
    await database.init_db()
    sid = await database.create_training_session(title="Buoi thu", agent_id=None)

    await database.update_training_session(
        sid, allowed_tools_json=json.dumps(["cut_anh_thu"]))

    session = await database.get_training_session(sid)
    assert session["allowed_tools_json"] == '["cut_anh_thu"]'
    listed = [s for s in await database.list_training_sessions() if s["id"] == sid][0]
    assert listed["allowed_tools_json"] == '["cut_anh_thu"]'


# ── Ảnh do công cụ tạo ra thì hiện thẳng trong chat ────────────────────────

async def test_chen_anh_cong_cu_tra_ve_vao_chat(tmp_path, monkeypatch):
    from api import websocket_training as wt
    data_root = tmp_path / "data"
    (data_root / "assets").mkdir(parents=True)
    img = data_root / "assets" / "ket-qua-cat.png"
    img.write_bytes(b"anh-da-cat")
    monkeypatch.setattr(wt, "_DATA_ROOT", data_root)
    monkeypatch.setattr(wt, "TRAINING_IMAGE_DIR", tmp_path / "training-images")

    ws = _FakeWS()
    reply = f"Em cắt xong rồi Sếp.\n\nFile kết quả: `{img}`"
    out = await wt._inline_local_images(ws, 7, reply)

    assert "![ket-qua-cat.png](/api/training/sessions/7/image/" in out
    assert any("![ket-qua-cat.png]" in (m.get("content") or "") for m in ws.sent)
    copied = list((tmp_path / "training-images" / "7").glob("*ket-qua-cat.png"))
    assert copied and copied[0].read_bytes() == b"anh-da-cat"


async def test_khong_lay_anh_ngoai_thu_muc_data(tmp_path, monkeypatch):
    """Học viên tự viết đường dẫn trong câu trả lời — không chặn là lôi được file
    bất kỳ trên máy vào khung chat."""
    from api import websocket_training as wt
    data_root = tmp_path / "data"
    data_root.mkdir()
    outside = tmp_path / "rieng-tu.png"
    outside.write_bytes(b"khong-duoc-lay")
    monkeypatch.setattr(wt, "_DATA_ROOT", data_root)
    monkeypatch.setattr(wt, "TRAINING_IMAGE_DIR", tmp_path / "training-images")

    ws = _FakeWS()
    reply = f"Ảnh nằm ở {outside}"
    assert await wt._inline_local_images(ws, 7, reply) == reply
    assert ws.sent == []


async def test_khong_chen_qua_nhieu_anh(tmp_path, monkeypatch):
    from api import websocket_training as wt
    data_root = tmp_path / "data"
    data_root.mkdir()
    paths = []
    for i in range(wt._MAX_INLINE_IMAGES + 2):
        p = data_root / f"anh{i}.png"
        p.write_bytes(b"x")
        paths.append(str(p))
    monkeypatch.setattr(wt, "_DATA_ROOT", data_root)
    monkeypatch.setattr(wt, "TRAINING_IMAGE_DIR", tmp_path / "training-images")

    out = await wt._inline_local_images(_FakeWS(), 7, " ".join(paths))
    assert out.count("![") == wt._MAX_INLINE_IMAGES
