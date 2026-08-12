"""Xanax viết marker [[XANAX:trigger_workflow|...]] trong phòng họp.

Xanax biết hai phương ngữ kích hoạt quy trình: marker (chat huấn luyện) và
trường "run_workflows" trong JSON (phòng họp). Nó học marker từ nội dung session
training được nhét vào ngữ cảnh, nên trong phòng họp vẫn viết marker vào giữa
"reply" và để "run_workflows" rỗng.

Quan sát thật trước khi sửa: quy trình KHÔNG chạy, marker hiện nguyên văn ra
màn hình, và vì lời Xanax được lưu lại nên lượt sau nó đọc lịch sử của chính
mình rồi bắt chước tiếp — vòng lặp tự củng cố. Ba tin nhắn trong DB đã dính.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_marker_trong_reply_duoc_quy_ve_run_workflows():
    """Đúng ca trên màn hình: reply có marker, run_workflows rỗng."""
    from api.websocket_meeting import _parse_orchestrator_json

    decision = _parse_orchestrator_json(json.dumps({
        "reply": 'Dạ chưa ạ, con xin lỗi Papa! Để con kích hoạt ngay bây giờ:\n\n'
                 '[[XANAX:trigger_workflow|task_id=14|input=Móc khóa con khỉ]]',
        "call_agents": [],
        "dismiss_agents": [],
        "run_workflows": [],
    }, ensure_ascii=False))

    # Quy trình phải thật sự được kích hoạt, không chỉ được nhắc tới
    assert decision["run_workflows"] == [{"task_id": 14, "input": "Móc khóa con khỉ"}]
    # Marker không được lọt ra màn hình
    assert "XANAX:" not in decision["reply"]
    assert "[[" not in decision["reply"]
    assert "con xin lỗi Papa" in decision["reply"]


def test_marker_khong_de_lai_dau_hai_cham_cut():
    """Gỡ marker xong không được để câu dẫn treo lửng."""
    from api.websocket_meeting import _parse_orchestrator_json

    decision = _parse_orchestrator_json(json.dumps({
        "reply": 'Con chạy ngay đây:\n\n[[XANAX:trigger_workflow|task_id=14|input=Lót ly]]',
        "run_workflows": [],
    }, ensure_ascii=False))
    assert decision["reply"] == "Con chạy ngay đây."


def test_marker_khong_lam_chay_hai_lan_khi_model_viet_ca_hai_kieu():
    """Model điền cả run_workflows lẫn marker cho CÙNG một việc."""
    from api.websocket_meeting import _parse_orchestrator_json

    decision = _parse_orchestrator_json(json.dumps({
        "reply": 'Chạy ngay ạ. [[XANAX:trigger_workflow|task_id=14|input=Móc khóa]]',
        "run_workflows": [{"task_id": 14, "input": "Móc khóa"}],
    }, ensure_ascii=False))
    assert decision["run_workflows"] == [{"task_id": 14, "input": "Móc khóa"}]


def test_marker_khac_viec_thi_chay_ca_hai():
    from api.websocket_meeting import _parse_orchestrator_json

    decision = _parse_orchestrator_json(json.dumps({
        "reply": 'Chạy cả hai ạ. [[XANAX:trigger_workflow|task_id=15|input=Bài B]]',
        "run_workflows": [{"task_id": 14, "input": "Bài A"}],
    }, ensure_ascii=False))
    assert decision["run_workflows"] == [
        {"task_id": 14, "input": "Bài A"},
        {"task_id": 15, "input": "Bài B"},
    ]


def test_marker_hong_thi_bo_qua_nhung_van_gỡ_khoi_loi_noi():
    """task_id không phải số → không chạy bừa, nhưng cũng không hiện ra màn hình."""
    from api.websocket_meeting import _parse_orchestrator_json

    decision = _parse_orchestrator_json(json.dumps({
        "reply": 'Con thử ạ. [[XANAX:trigger_workflow|task_id=abc|input=X]]',
        "run_workflows": [],
    }, ensure_ascii=False))
    assert decision["run_workflows"] == []
    assert "XANAX:" not in decision["reply"]


def test_marker_khac_khong_chay_duoc_van_phai_go_khoi_man_hinh():
    """Phòng họp không làm được save_note, nhưng chuỗi kỹ thuật không được lộ."""
    from api.websocket_meeting import _parse_orchestrator_json

    decision = _parse_orchestrator_json(json.dumps({
        "reply": 'Con ghi nhớ ạ. [[XANAX:save_note|content=Papa thích màu xanh]]',
        "run_workflows": [],
    }, ensure_ascii=False))
    assert decision["run_workflows"] == []
    assert "XANAX:" not in decision["reply"]
    assert "Con ghi nhớ ạ." in decision["reply"]


def test_marker_trong_output_khong_phai_json():
    """Model trả text trần kèm marker (không JSON) vẫn phải chạy được."""
    from api.websocket_meeting import _parse_orchestrator_json

    decision = _parse_orchestrator_json(
        'Dạ con chạy ngay. [[XANAX:trigger_workflow|task_id=14|input=Móc khóa con khỉ]]')
    assert decision["run_workflows"] == [{"task_id": 14, "input": "Móc khóa con khỉ"}]
    assert "XANAX:" not in decision["reply"]


# ── Nửa còn lại: Xanax HỨA sẽ chạy rồi không chạy ────────────────────────────


def test_loi_hua_suong_bi_dinh_chinh():
    """Đúng tin nhắn 00:23 trên màn hình: hứa "sẽ kích hoạt ngay", không gì chạy."""
    from api.websocket_meeting import _guard_false_run_claim

    reply = ('Dạ, con sẽ kích hoạt quy trình "Đăng bài lên fanpage" với chủ đề '
             '"móc khóa con khỉ" ngay ạ.')
    out = _guard_false_run_claim(reply, [], asked_to_run=True)
    assert out != reply
    assert "CHƯA có quy trình nào được kích hoạt" in out


def test_hua_ma_chay_that_thi_khong_dinh_chinh():
    from api.websocket_meeting import _guard_false_run_claim

    reply = 'Dạ, con sẽ kích hoạt quy trình "Đăng bài lên fanpage" ngay ạ.'
    out = _guard_false_run_claim(reply, [{"task_id": 14, "input": "x"}], asked_to_run=True)
    assert out == reply


def test_khong_dinh_chinh_khi_ceo_khong_bao_chay():
    from api.websocket_meeting import _guard_false_run_claim

    reply = 'Con sẽ chạy lại quy trình đó sau khi Papa duyệt bài ạ.'
    out = _guard_false_run_claim(reply, [], asked_to_run=False)
    assert out == reply


def test_cau_hoi_lai_chu_de_khong_bi_coi_la_hua():
    """Xanax hỏi lại vì thiếu chủ đề — đúng hành vi, không được dán cảnh báo."""
    from api.websocket_meeting import _promises_workflow_run

    assert not _promises_workflow_run(
        "Dạ con chưa rõ Papa muốn chủ đề gì, Papa cho con xin chủ đề nha.")
    assert not _promises_workflow_run(
        "Papa muốn con kích hoạt lại quy trình không, hay để Papa xử lý phần ảnh trước?")


def test_moi_nhan_vien_khong_bi_coi_la_hua_chay_quy_trinh():
    from api.websocket_meeting import _promises_workflow_run

    assert not _promises_workflow_run("Để con mời trưởng phòng Marketing vào trao đổi.")


def test_marker_lam_quy_trinh_chay_that_nen_khong_con_dinh_chinh():
    """Hai lớp sửa phải ăn khớp: marker -> chạy thật -> không còn cảnh báo."""
    import json as _json
    from api.websocket_meeting import _parse_orchestrator_json, _guard_false_run_claim

    decision = _parse_orchestrator_json(_json.dumps({
        "reply": 'Để con kích hoạt ngay bây giờ:\n[[XANAX:trigger_workflow|task_id=14|input=Móc khóa con khỉ]]',
        "run_workflows": [],
    }, ensure_ascii=False))
    out = _guard_false_run_claim(decision["reply"], decision["run_workflows"],
                                 asked_to_run=True)
    assert decision["run_workflows"] == [{"task_id": 14, "input": "Móc khóa con khỉ"}]
    assert "Trạng thái thật" not in out
    assert "Đính chính" not in out
