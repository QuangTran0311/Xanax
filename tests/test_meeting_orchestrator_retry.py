"""Model bỏ qua system prompt và trả lời như một trợ lý vô danh.

Quan sát thật (phòng họp 18, 2026-08-06 19:14): Papa bảo chạy quy trình, Xanax
đáp "Chào bạn, tôi hiểu bạn muốn... Tuy nhiên tôi hiện không có khả năng kích
hoạt hoặc chạy bất kỳ quy trình nào... Có vẻ như bạn đang tương tác với một
chatbot tự động." Mất cả danh tính lẫn năng lực — trong khi SOUL vẫn đủ 17k ký
tự và lần gọi ngay sau đó lại đúng vai. Tức là model lú một lượt, không phải
cấu hình hỏng.

Vấn đề nằm ở đường fallback: nó đổ NGUYÊN VĂN đoạn văn xuôi đó ra phòng họp,
nên một lượt model lú là Papa đọc được lời Xanax phủ nhận chính năng lực của
mình. Nay phát hiện được và thử lại đúng một lần.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Nguyên văn lời Xanax đã nói trong phòng họp, rút gọn.
LOI_MAT_DANH_TINH = (
    'Chào bạn, tôi hiểu bạn muốn tôi kích hoạt quy trình "Đăng bài lên fanpage" với '
    'chủ đề "túi xách bằng len". Tuy nhiên, tôi cần nhấn mạnh rằng tôi hiện không có '
    'khả năng kích hoạt hoặc chạy bất kỳ quy trình, tác vụ thực tế nào trong hệ thống '
    'này. Có vẻ như bạn đang tương tác với một chatbot tự động.'
)


def test_nhan_ra_loi_van_xuoi_mat_danh_tinh():
    from api.websocket_meeting import _has_orchestrator_json

    assert _has_orchestrator_json(LOI_MAT_DANH_TINH) is False


def test_nhan_ra_json_hop_le():
    from api.websocket_meeting import _has_orchestrator_json

    full = json.dumps({"reply": "Dạ Papa, con chạy ngay ạ.", "call_agents": [],
                       "dismiss_agents": [], "run_workflows": [{"task_id": 14, "input": "x"}]},
                      ensure_ascii=False)
    assert _has_orchestrator_json(full) is True
    # Thiếu call_agents/run_workflows là bình thường khi không cần gọi ai
    assert _has_orchestrator_json('{"reply": "Dạ Papa con nghe ạ"}') is True


def test_json_lan_trong_van_xuoi_van_tinh_la_hop_le():
    """Model hay kẹp JSON giữa lời dẫn; _parse_orchestrator_json vẫn đọc được."""
    from api.websocket_meeting import _has_orchestrator_json

    assert _has_orchestrator_json('Đây ạ: {"reply": "ok"} — hết.') is True


def test_cac_dang_hong_khac_deu_bi_tu_choi():
    from api.websocket_meeting import _has_orchestrator_json

    assert _has_orchestrator_json("") is False
    assert _has_orchestrator_json('{"reply": "thiếu ngoặc đóng"') is False
    assert _has_orchestrator_json('{"call_agents": [1]}') is False   # không có reply
    assert _has_orchestrator_json('["reply"]') is False              # không phải object


def test_thu_lai_mot_lan_khi_model_tra_van_xuoi(monkeypatch):
    """Lượt hỏng phải được thử lại, và lượt thử lại đúng thì dùng kết quả đó."""
    import asyncio
    import api.websocket_meeting as wm

    goi = []
    tra_ve = [
        LOI_MAT_DANH_TINH,                                     # lượt 1: hỏng
        json.dumps({"reply": "Dạ Papa, con chạy ngay ạ.",
                    "run_workflows": [{"task_id": 14, "input": "túi xách bằng len"}]},
                   ensure_ascii=False),                        # lượt 2: đúng
    ]

    async def fake_complete(messages):
        goi.append(messages)
        return tra_ve[len(goi) - 1]

    monkeypatch.setattr(wm.hermes, "complete_with_context", fake_complete)
    monkeypatch.setattr(wm, "_soul_and_live_context", _async_const("SOUL giả"))
    monkeypatch.setattr(wm, "_build_roster_text", _async_const(""))
    monkeypatch.setattr(wm, "_build_workflow_roster_text", _async_const(""))
    monkeypatch.setattr(wm, "get_agent_configs_by_ids", _async_const([]))

    d = asyncio.run(wm._xanax_orchestrate(
        [{"role": "user", "content": "chạy quy trình đăng bài lên fanpage với túi xách bằng len"}],
        [],
    ))

    assert len(goi) == 2, "phải thử lại đúng 1 lần"
    assert d["run_workflows"] == [{"task_id": 14, "input": "túi xách bằng len"}]
    assert "chatbot tự động" not in d["reply"]


def test_khong_thu_lai_khi_luot_dau_da_dung(monkeypatch):
    """Không được gọi model thừa — mỗi lượt thừa là thêm tiền và thêm độ trễ."""
    import asyncio
    import api.websocket_meeting as wm

    goi = []

    async def fake_complete(messages):
        goi.append(messages)
        return json.dumps({"reply": "Dạ Papa.", "run_workflows": []}, ensure_ascii=False)

    monkeypatch.setattr(wm.hermes, "complete_with_context", fake_complete)
    monkeypatch.setattr(wm, "_soul_and_live_context", _async_const("SOUL giả"))
    monkeypatch.setattr(wm, "_build_roster_text", _async_const(""))
    monkeypatch.setattr(wm, "_build_workflow_roster_text", _async_const(""))
    monkeypatch.setattr(wm, "get_agent_configs_by_ids", _async_const([]))

    asyncio.run(wm._xanax_orchestrate([{"role": "user", "content": "chào con"}], []))
    assert len(goi) == 1


def test_thu_lai_van_hong_thi_khong_treo_phong_hop(monkeypatch):
    """Hai lượt đều hỏng thì chấp nhận nguyên văn — thà xấu còn hơn treo."""
    import asyncio
    import api.websocket_meeting as wm

    goi = []

    async def fake_complete(messages):
        goi.append(messages)
        return LOI_MAT_DANH_TINH

    monkeypatch.setattr(wm.hermes, "complete_with_context", fake_complete)
    monkeypatch.setattr(wm, "_soul_and_live_context", _async_const("SOUL giả"))
    monkeypatch.setattr(wm, "_build_roster_text", _async_const(""))
    monkeypatch.setattr(wm, "_build_workflow_roster_text", _async_const(""))
    monkeypatch.setattr(wm, "get_agent_configs_by_ids", _async_const([]))

    d = asyncio.run(wm._xanax_orchestrate([{"role": "user", "content": "chạy quy trình"}], []))
    assert len(goi) == 2, "chỉ thử lại 1 lần, không lặp vô hạn"
    assert d["reply"]           # vẫn có lời để hiển thị, không rỗng
    assert d["run_workflows"] == []


def _async_const(value):
    async def _f(*a, **k):
        return value
    return _f
