"""Bài học Papa dạy phải thắng khuôn mẫu viết sẵn trong mô tả kỹ năng.

Ca thật khiến phải làm việc này: Papa dạy Celexa "khi câu đã đủ duyên thì dừng,
không thêm vế thúc đẩy mua hàng ở cuối", trong khi kỹ năng `write_post` ghi cứng
"CTA: câu kêu gọi hành động rõ ràng (comment / tag bạn / nhắn tin)". Bài đăng
sinh ra kết thúc bằng đúng câu CTA đó — model theo kỹ năng, bỏ bài học.

Vì sao model chọn kỹ năng: kỹ năng là công thức từng bước rất dễ làm theo, bài
học là nguyên tắc. Thứ tự ghép prompt không cứu được — soul đã nằm cuối cùng mà
vẫn thua. Phải nói thẳng cái nào thắng.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def soul_dir(tmp_path, monkeypatch):
    from core import agent_soul
    monkeypatch.setattr(agent_soul, "SOULS_DIR", tmp_path)
    return tmp_path


def _agent(aid=1, name="Celexa"):
    return {"id": aid, "name": name, "role": "Content", "system_prompt": ""}


def test_co_bai_hoc_thi_prompt_kem_dong_uu_tien(soul_dir):
    from core.agent_soul import ensure_soul_file, append_lessons, soul_for_prompt

    ensure_soul_file(_agent())
    append_lessons(1, "Celexa", "Dạy hook",
                   ["Khi câu đã đủ duyên thì dừng, không thêm vế thúc đẩy mua hàng."])

    prompt = soul_for_prompt(1)
    assert "Khi câu đã đủ duyên" in prompt
    assert "ĐÈ LÊN" in prompt, "phải nói rõ bài học thắng khuôn mẫu kỹ năng"
    assert "kêu gọi hành động" in prompt, "phải nêu ví dụ cụ thể để model nhận ra"


def test_chua_duoc_day_thi_khong_them_gi(soul_dir):
    """Nhân viên chưa học buổi nào mà đọc câu ưu tiên thì chỉ tổ nhiễu prompt."""
    from core.agent_soul import ensure_soul_file, soul_for_prompt, read_soul

    ensure_soul_file(_agent(2, "Lexapro"))
    assert soul_for_prompt(2) == read_soul(2)
    assert "ĐÈ LÊN" not in soul_for_prompt(2)


def test_khoi_bai_hoc_rong_cung_tinh_la_chua_day(soul_dir):
    """File có sẵn khối nhưng chưa ghi gì — không được coi là đã dạy."""
    from core.agent_soul import ensure_soul_file, has_lessons, soul_for_prompt

    ensure_soul_file(_agent(3, "Prozac"))
    assert has_lessons(3) is False
    assert "ĐÈ LÊN" not in soul_for_prompt(3)


def test_soul_cu_khong_co_khoi_bai_hoc(soul_dir):
    from core.agent_soul import has_lessons, soul_for_prompt

    (soul_dir / "agent_9.md").write_text("# Soul — Cũ\n\nViết hay.\n", encoding="utf-8")
    assert has_lessons(9) is False
    assert soul_for_prompt(9) == "# Soul — Cũ\n\nViết hay.\n"


def test_khong_co_file_soul_thi_tra_rong(soul_dir):
    from core.agent_soul import soul_for_prompt

    assert soul_for_prompt(999) == ""


def test_sync_du_lieu_khong_lam_mat_bai_hoc(soul_dir):
    """sync_agent_soul chạy trước MỖI lần nhân viên làm việc — không được xoá bài học."""
    import asyncio
    from core.agent_soul import ensure_soul_file, append_lessons, sync_agent_soul, read_soul

    agent = _agent(4, "Zoloft")
    ensure_soul_file(agent)
    append_lessons(4, "Zoloft", "Buổi 1", ["Bài học phải sống sót qua sync."])

    asyncio.run(sync_agent_soul(agent))
    assert "Bài học phải sống sót qua sync." in read_soul(4)
