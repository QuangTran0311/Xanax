"""Phòng dạy AI có học viên: chọn 1 nhân viên, kết thúc thì ghi bài học vào soul.

Ba ranh giới quan trọng nhất được khoá ở đây:

1. Chưng cất và ghi soul là HAI bước tách rời. Ghi vào soul ảnh hưởng mọi lần
   nhân viên làm việc sau đó, nên bản tóm của model phải qua tay Papa đã.
2. Bài học buổi dạy nằm ở khối riêng, không trộn với khối ĐẠT/KHÔNG ĐẠT — khối
   kia bị cắt còn 40 mục gần nhất và sẽ đẩy bài học Papa dạy ra ngoài.
3. Chưng cất phải dám trả mảng rỗng. Bịa ra bài học nghe hay là kiểu hỏng tệ
   nhất ở đây vì nó vào soul rồi thì không ai biết nó từ đâu ra.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── Chưng cất: đọc JSON của model ────────────────────────────────────────────

def _texts(lessons):
    return [x["text"] for x in lessons]


def test_doc_duoc_danh_sach_bai_hoc():
    from api.routes.training import _parse_lessons

    raw = json.dumps({"lessons": [
        {"text": "Viết caption dưới 100 chữ.", "scope": "skill", "skill": "write_post"},
        {"text": "Gọi khách là 'mấy bà'.", "scope": "project"},
    ]}, ensure_ascii=False)
    assert _parse_lessons(raw) == [
        {"text": "Viết caption dưới 100 chữ.", "scope": "skill", "skill": "write_post"},
        {"text": "Gọi khách là 'mấy bà'.", "scope": "project", "skill": ""},
    ]


def test_model_tra_mang_chuoi_kieu_cu_van_nhan_duoc():
    """Model bỏ qua phần phạm vi thì bài học vẫn phải giữ, mặc định về nhân viên
    — đúng bằng hành vi trước khi có phạm vi, không mất gì Papa đã dạy."""
    from api.routes.training import _parse_lessons

    raw = json.dumps({"lessons": ["Bài A", "Bài B"]}, ensure_ascii=False)
    assert _parse_lessons(raw) == [
        {"text": "Bài A", "scope": "agent", "skill": ""},
        {"text": "Bài B", "scope": "agent", "skill": ""},
    ]


def test_pham_vi_la_ru_thi_ve_nhan_vien():
    """Phạm vi lạ mà đoán bừa thì có ngày giọng thương hiệu chui vào kỹ năng dùng
    chung; về "agent" là lựa chọn hẹp nhất và an toàn nhất."""
    from api.routes.training import _parse_lessons

    raw = json.dumps({"lessons": [{"text": "Bài A", "scope": "toàn công ty"}]},
                     ensure_ascii=False)
    assert _parse_lessons(raw) == [{"text": "Bài A", "scope": "agent", "skill": ""}]


def test_model_bao_khong_hoc_duoc_gi_thi_tra_rong():
    """Mảng rỗng là câu trả lời hợp lệ, không được biến thành bài học bịa."""
    from api.routes.training import _parse_lessons

    assert _parse_lessons(json.dumps({"lessons": []})) == []


def test_model_tra_rac_thi_khong_vo_va_khong_bia():
    from api.routes.training import _parse_lessons

    assert _parse_lessons("xin lỗi Papa con không tóm được ạ") == []
    assert _parse_lessons("") == []
    assert _parse_lessons('{"lessons": "không phải mảng"}') == []


def test_bo_muc_rong_va_cat_khoang_trang():
    from api.routes.training import _parse_lessons

    raw = json.dumps({"lessons": ["  Bài A  ", "", "   ", "Bài B"]}, ensure_ascii=False)
    assert _texts(_parse_lessons(raw)) == ["Bài A", "Bài B"]


# ── Ghi vào soul ─────────────────────────────────────────────────────────────

@pytest.fixture
def soul_dir(tmp_path, monkeypatch):
    from core import agent_soul
    monkeypatch.setattr(agent_soul, "SOULS_DIR", tmp_path)
    return tmp_path


def test_ghi_bai_hoc_vao_khoi_rieng_khong_dung_khoi_dat_khong_dat(soul_dir):
    from core.agent_soul import ensure_soul_file, append_lessons, append_feedback, read_soul

    agent = {"id": 42, "name": "Celexa", "role": "Content", "system_prompt": "Bạn viết content."}
    ensure_soul_file(agent)
    append_feedback(42, "Celexa", "Đăng bài", "fail", "Bài quá dài", "Papa muốn ngắn hơn")
    append_lessons(42, "Celexa", "Dạy viết caption", ["Viết caption dưới 100 chữ."])

    text = read_soul(42)
    lesson_block = text.split("<!-- AGENT_LESSON_START -->")[1].split("<!-- AGENT_LESSON_END -->")[0]
    feedback_block = text.split("<!-- AGENT_FEEDBACK_START -->")[1].split("<!-- AGENT_FEEDBACK_END -->")[0]

    assert "Viết caption dưới 100 chữ." in lesson_block
    assert "Viết caption dưới 100 chữ." not in feedback_block
    assert "Bài quá dài" in feedback_block
    assert "Bài quá dài" not in lesson_block


def test_nhieu_buoi_day_cong_don_khong_de_len_nhau(soul_dir):
    from core.agent_soul import ensure_soul_file, append_lessons, read_soul

    agent = {"id": 7, "name": "Prozac", "role": "SEO", "system_prompt": ""}
    ensure_soul_file(agent)
    append_lessons(7, "Prozac", "Buổi 1", ["Bài học một."])
    append_lessons(7, "Prozac", "Buổi 2", ["Bài học hai."])

    text = read_soul(7)
    assert "Bài học một." in text
    assert "Bài học hai." in text
    assert "Buổi 1" in text and "Buổi 2" in text


def test_khong_ghi_gi_khi_danh_sach_rong(soul_dir):
    from core.agent_soul import ensure_soul_file, append_lessons, read_soul

    ensure_soul_file({"id": 9, "name": "X", "role": "", "system_prompt": ""})
    before = read_soul(9)
    assert append_lessons(9, "X", "Buổi trống", []) == 0
    assert append_lessons(9, "X", "Buổi trống", ["   ", ""]) == 0
    assert read_soul(9) == before


def test_soul_cu_thieu_khoi_bai_hoc_van_ghi_duoc(soul_dir):
    """File soul tạo trước tính năng này không có khối LESSON — không được mất dữ liệu."""
    from core.agent_soul import append_lessons, read_soul

    old = soul_dir / "agent_5.md"
    old.write_text(
        "# Soul — Cũ\n\n## Mô tả & Tính cách\nViết hay.\n\n"
        "<!-- AGENT_DATA_START -->\n<!-- AGENT_DATA_END -->\n",
        encoding="utf-8",
    )
    assert append_lessons(5, "Cũ", "Buổi mới", ["Bài học mới."]) == 1

    text = read_soul(5)
    assert "Bài học mới." in text
    assert "Viết hay." in text          # phần viết tay không được đụng vào
    assert "<!-- AGENT_DATA_START -->" in text


def test_ghi_kem_ten_buoi_day_de_lan_lai_nguon_goc(soul_dir):
    from core.agent_soul import ensure_soul_file, append_lessons, read_soul

    ensure_soul_file({"id": 3, "name": "Y", "role": "", "system_prompt": ""})
    append_lessons(3, "Y", "Dạy cách đặt tiêu đề", ["Tiêu đề nên có số."], taught_at="2026-08-07")
    text = read_soul(3)
    assert "Dạy cách đặt tiêu đề" in text
    assert "2026-08-07" in text


# ── Tách phần đúc kết Papa đã sửa thành từng bài học ─────────────────────────
#
# Phòng chỉ đóng khi Papa bấm "Lưu bài học kinh nghiệm"; bấm Đạt / Cần cải thiện
# trước đó chỉ dựng bản nháp. Nội dung ghi vào soul là thứ Papa gõ trong ô, nên
# việc tách dòng phải chịu được mọi kiểu Papa viết tay.


def test_moi_dong_la_mot_bai_hoc():
    from api.routes.training import _lessons_from_notes

    assert _texts(_lessons_from_notes("Bài A\nBài B")) == ["Bài A", "Bài B"]


def test_bo_dau_dau_dong_de_soul_khong_bi_hai_gach():
    """append_lessons tự thêm '- ', không bỏ thì soul ra '- - Bài học'."""
    from api.routes.training import _lessons_from_notes

    notes = "- Bài A\n* Bài B\n• Bài C\n1. Bài D\n2) Bài E"
    assert _texts(_lessons_from_notes(notes)) == ["Bài A", "Bài B", "Bài C", "Bài D", "Bài E"]


def test_bo_dong_trong_va_khoang_trang_thua():
    from api.routes.training import _lessons_from_notes

    assert _texts(_lessons_from_notes("  Bài A  \n\n   \n-   \nBài B\n")) == ["Bài A", "Bài B"]


def test_o_duc_ket_de_trong_thi_khong_ghi_gi():
    from api.routes.training import _lessons_from_notes

    assert _lessons_from_notes("") == []
    assert _lessons_from_notes("   \n\n  ") == []


def test_dau_gach_giua_cau_khong_bi_cat():
    """Chỉ dấu ĐẦU DÒNG mới là bullet; gạch trong câu là nội dung."""
    from api.routes.training import _lessons_from_notes

    assert _texts(_lessons_from_notes("Xưng hô - phải linh hoạt")) == ["Xưng hô - phải linh hoạt"]
