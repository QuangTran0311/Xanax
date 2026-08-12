"""
Tests — Xanax không được nói "đã chạy quy trình" khi chưa chạy gì.

Thứ thật sự kích hoạt quy trình là mảng `run_workflows` trong JSON điều phối.
Lời Xanax nói chỉ là chữ do model sinh ra. System prompt đã dặn "TUYỆT ĐỐI không
nói là đã chạy nếu để run_workflows rỗng", nhưng dặn không phải là ép — model
vẫn nói sai, và người dùng ngồi chờ một quy trình chưa hề khởi động.
"""
import pytest

from api.websocket_meeting import (
    _claims_workflow_ran,
    _guard_false_run_claim,
    _parse_orchestrator_json,
)


class TestClaimsWorkflowRan:
    @pytest.mark.parametrize("reply", [
        # Câu thật Xanax đã nói trong phòng họp trong khi run_workflows rỗng.
        "Dạ, con đã chạy lại quy trình \"Đăng bài lên fanpage\" (#14) với chủ đề "
        "\"móc khóa cỏ 4 lá\" rồi nha Papa. Để con theo dõi kết quả và báo lại cho Papa ạ.",
        "Con vừa kích hoạt quy trình Đăng bài lên fanpage.",
        "Quy trình đã được chạy rồi ạ.",
        "Con đang chạy tác vụ #13 cho Papa.",
        "Đã trigger workflow #14.",
    ])
    def test_detects_claim(self, reply):
        assert _claims_workflow_ran(reply)

    @pytest.mark.parametrize("reply", [
        # Hứa/hỏi thì KHÔNG phải khẳng định — chặn nhầm sẽ làm phiền người dùng
        # bằng đính chính vô nghĩa.
        "Papa muốn con kích hoạt lại quy trình không ạ?",
        # Câu thật Xanax đã hỏi: có đủ "kích hoạt", "quy trình" và "rồi", nhưng
        # là đang xin ý kiến. Bắt nhầm câu này là đính chính một lời chưa hề nói.
        "Dạ Papa, quy trình 'Đăng bài lên fanpage' vừa chạy bị lỗi ở bước tạo ảnh. "
        "Papa muốn con kích hoạt lại quy trình không, hay để Papa xử lý phần ảnh "
        "trước rồi chạy lại sau?",
        "Papa có muốn Celexa viết post trước phần chữ không ạ?",
        "Dạ con chưa rõ Papa muốn chủ đề gì, Papa cho con xin chủ đề nha.",
        "Để con mời trưởng phòng Marketing vào trao đổi.",
        "",
    ])
    def test_ignores_non_claims(self, reply):
        assert not _claims_workflow_ran(reply)


class TestGuardFalseRunClaim:
    def test_appends_correction_when_nothing_ran(self):
        reply = "Dạ, con đã chạy lại quy trình \"Đăng bài lên fanpage\" (#14) rồi nha Papa."
        out = _guard_false_run_claim(reply, [])
        assert out.startswith(reply), "phải giữ nguyên lời gốc để người dùng thấy Xanax đã nói gì"
        assert "CHƯA" in out
        assert len(out) > len(reply)

    def test_silent_when_workflow_actually_ran(self):
        """Chạy thật thì câu xác nhận do _run_workflows_from_meeting sinh ra —
        không được chèn đính chính vào đó."""
        reply = "Dạ, con đã chạy lại quy trình #14 rồi nha Papa."
        assert _guard_false_run_claim(reply, [{"task_id": 14, "input": "x"}]) == reply

    def test_silent_when_reply_makes_no_claim(self):
        reply = "Papa muốn con kích hoạt lại quy trình không ạ?"
        assert _guard_false_run_claim(reply, []) == reply

    def test_handles_empty_reply(self):
        assert _guard_false_run_claim("", []) == ""

    def test_correction_names_what_to_do_next(self):
        """Đính chính phải nói được cách sửa, không chỉ báo là sai."""
        out = _guard_false_run_claim("Con đã chạy quy trình rồi ạ.", [])
        assert "tên quy trình" in out and "chủ đề" in out


class TestParseFallbackAlsoGuarded:
    """Model trả prose thay vì JSON → fallback coi cả câu là `reply` và
    run_workflows rỗng. Rào chắn phải bắt được cả đường này."""

    def test_prose_claiming_run_is_corrected(self):
        decision = _parse_orchestrator_json(
            "Dạ con đã kích hoạt quy trình Đăng bài lên fanpage cho Papa rồi ạ."
        )
        assert decision["run_workflows"] == []
        out = _guard_false_run_claim(decision["reply"], decision["run_workflows"])
        assert "CHƯA" in out

    def test_valid_json_with_real_run_is_untouched(self):
        decision = _parse_orchestrator_json(
            '{"reply": "Dạ con đã chạy quy trình rồi ạ.", "call_agents": [], '
            '"dismiss_agents": [], "run_workflows": [{"task_id": 14, "input": "móc khóa"}]}'
        )
        assert decision["run_workflows"] == [{"task_id": 14, "input": "móc khóa"}]
        out = _guard_false_run_claim(decision["reply"], decision["run_workflows"])
        assert out == decision["reply"]


class TestReportVsClaim:
    """Kể lại lần chạy trước ≠ khẳng định vừa kích hoạt. Đính chính vào câu báo
    hỏng là sai — lần chạy đó có thật, chỉ là nó hỏng."""

    @pytest.mark.parametrize("reply", [
        "Quy trình 'Đăng bài lên fanpage' vừa chạy bị lỗi ở bước tạo ảnh.",
        "Quy trình đã chạy nhưng thất bại ở bước 2/2.",
        "Tác vụ đã chạy xong nhưng dừng lại vì thiếu ảnh.",
    ])
    def test_failure_report_is_not_a_claim(self, reply):
        assert not _claims_workflow_ran(reply)
        assert _guard_false_run_claim(reply, []) == reply

    def test_still_catches_claim_in_same_paragraph_as_report(self):
        """Đoạn vừa báo hỏng vừa khẳng định đã chạy lại — phải bắt vế thứ hai."""
        reply = (
            "Quy trình 'Đăng bài lên fanpage' vừa chạy bị lỗi ở bước tạo ảnh. "
            "Con đã chạy lại quy trình #14 cho Papa rồi ạ."
        )
        assert _claims_workflow_ran(reply)
        assert "CHƯA" in _guard_false_run_claim(reply, [])


class TestOnlyCorrectWhenAskedToRun:
    """Chỉ đính chính khi CEO thật sự bảo chạy quy trình ở lượt này.

    Đã đính chính oan: CEO hỏi cách HUỶ quy trình, Xanax đáp "quy trình #14 vừa
    được kích hoạt và đang chạy" — đúng sự thật, nó kể lại lần kích hoạt trước —
    và bị dán thêm "thực tế CHƯA có quy trình nào được kích hoạt".
    """

    REPLY = ('Dạ, hiện tại hệ thống chưa có chức năng hủy quy trình đã kích hoạt, Papa ạ. '
             'Quy trình "Đăng bài lên fanpage" (#14) vừa được kích hoạt và đang chạy.')

    def test_no_correction_when_user_did_not_ask_to_run(self):
        assert _guard_false_run_claim(self.REPLY, [], asked_to_run=False) == self.REPLY

    def test_still_corrects_when_user_asked_to_run(self):
        out = _guard_false_run_claim(self.REPLY, [], asked_to_run=True)
        assert "CHƯA" in out

    def test_real_run_never_corrected_either_way(self):
        ran = [{"task_id": 14, "input": "x"}]
        assert _guard_false_run_claim(self.REPLY, ran, asked_to_run=True) == self.REPLY
        assert _guard_false_run_claim(self.REPLY, ran, asked_to_run=False) == self.REPLY

    def test_asking_to_cancel_is_not_a_run_command(self):
        """Chính câu CEO gõ ra lỗi này: 'huỷ' không phải lệnh chạy."""
        from api.websocket_meeting import _is_workflow_command
        assert not _is_workflow_command("hủy quy trình đăng bài lên fanpage đi")
        assert _is_workflow_command("chạy quy trình đăng bài lên fanpage")
