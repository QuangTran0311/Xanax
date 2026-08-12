"""
Tests — thông báo hệ thống đẩy vào phòng họp.

Hai thứ được khoá ở đây:
- Kết quả cuối của quy trình phải được LƯU vào lịch sử họp, vì bong bóng tiến độ
  chỉ sống trong phiên đang mở; ai vào sau sẽ không thấy gì.
- Không được lưu trùng. Một bước hỏng phát ra `agent_error` rồi `run_failed`
  mang cùng một câu lỗi, nên phòng họp từng nhận hai tin nhắn giống hệt nhau.
"""
import pytest

from api.websocket_workflow import _meeting_progress_sender


@pytest.fixture
def captured(monkeypatch):
    saved: list[tuple] = []
    pushed: list[str] = []

    async def fake_add(meeting_id, sender, sender_type, content):
        saved.append((meeting_id, sender, sender_type, content))
        return len(saved)

    async def fake_notice(meeting_id, text):
        pushed.append(text)

    async def fake_progress(meeting_id, payload):
        pass

    monkeypatch.setattr("api.websocket_workflow.add_meeting_message", fake_add)
    monkeypatch.setattr("api.websocket_meeting.push_meeting_notice", fake_notice)
    monkeypatch.setattr("api.websocket_meeting.push_meeting_progress", fake_progress)
    return {"saved": saved, "pushed": pushed}


async def _drive(events):
    seen = []

    async def inner(msg):
        seen.append(msg)

    send = _meeting_progress_sender(meeting_id=1, inner=inner)
    for e in events:
        await send(e)
    return seen


class TestSystemNoticePersisted:
    @pytest.mark.asyncio
    async def test_run_done_is_saved_as_system_message(self, captured):
        await _drive([
            {"type": "run_started", "run_id": 5, "task_name": "Đăng bài", "steps": [{}]},
            {"type": "run_done", "run_id": 5},
        ])
        assert len(captured["saved"]) == 1
        meeting_id, sender, sender_type, content = captured["saved"][0]
        assert (meeting_id, sender, sender_type) == (1, "Hệ thống", "system")
        assert content == 'Quy trình "Đăng bài": Đã chạy xong.'
        assert captured["pushed"] == [content], "phải đẩy đúng nội dung đã lưu"

    @pytest.mark.asyncio
    async def test_running_steps_are_not_saved(self, captured):
        """Tiến độ giữa chừng chỉ là bong bóng sống trong phiên, không lưu."""
        await _drive([
            {"type": "run_started", "run_id": 5, "task_name": "Đăng bài", "steps": [{}]},
            {"type": "agent_start", "run_id": 5, "agent_name": "Zoloft", "step": 1},
            {"type": "agent_done", "run_id": 5, "agent_name": "Zoloft"},
        ])
        assert captured["saved"] == []


class TestNoDuplicateNotice:
    @pytest.mark.asyncio
    async def test_same_error_from_two_events_saved_once(self, captured):
        """`agent_error` rồi `run_failed` mang cùng một câu lỗi — người dùng từng
        thấy hai tin nhắn dài giống hệt nhau nằm cạnh nhau."""
        err = "Nhân viên này có công cụ BẮT BUỘC nhưng KHÔNG gọi"
        await _drive([
            {"type": "run_started", "run_id": 5, "task_name": "Tạo post và ảnh", "steps": [{}]},
            {"type": "agent_error", "run_id": 5, "content": err},
            {"type": "run_failed", "run_id": 5, "content": err},
        ])
        assert len(captured["saved"]) == 1, captured["saved"]
        assert len(captured["pushed"]) == 1

    @pytest.mark.asyncio
    async def test_different_messages_both_saved(self, captured):
        """Chống trùng không được nuốt mất thông báo khác nội dung."""
        await _drive([
            {"type": "run_started", "run_id": 5, "task_name": "Tạo post và ảnh", "steps": [{}]},
            {"type": "agent_error", "run_id": 5, "content": "Lỗi bước 1"},
            {"type": "run_failed", "run_id": 5, "content": "Lỗi bước 2"},
        ])
        assert len(captured["saved"]) == 2

    @pytest.mark.asyncio
    async def test_same_text_again_after_something_else_is_saved(self, captured):
        """Chỉ bỏ trùng LIÊN TIẾP. Cùng một câu xuất hiện lại sau một thông báo
        khác là chuyện có thật, không được nuốt."""
        await _drive([
            {"type": "run_started", "run_id": 5, "task_name": "T", "steps": [{}]},
            {"type": "run_failed", "run_id": 5, "content": "Lỗi A"},
            {"type": "run_failed", "run_id": 5, "content": "Lỗi B"},
            {"type": "run_failed", "run_id": 5, "content": "Lỗi A"},
        ])
        assert len(captured["saved"]) == 3
