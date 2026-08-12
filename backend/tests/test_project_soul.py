"""Giọng thương hiệu thuộc về DỰ ÁN, không thuộc về nhân viên hay kỹ năng.

Ca thật khiến phải làm việc này: Papa dạy Celexa cách viết bài cho shop len
handmade. Trước đây bài học đó chỉ có hai chỗ để đi:

- ghi vào kỹ năng write_post → nhân viên khác dùng chung kỹ năng cũng bị lây
  giọng shop len, kỹ năng hết dùng lại được;
- ghi vào soul Celexa → chính Celexa sang dự án bán nội thất vẫn nói giọng
  shop len.

Ba bài test đầu khoá đúng ba ranh giới đó: cái gì đi về đâu, và cái gì KHÔNG
được đi đâu.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def souls(tmp_path, monkeypatch):
    """Ba kho soul trỏ vào thư mục tạm để test không đụng data thật."""
    from core import agent_soul, project_soul, skill_soul
    monkeypatch.setattr(agent_soul, "SOULS_DIR", tmp_path / "agents")
    monkeypatch.setattr(project_soul, "PROJECT_SOULS_DIR", tmp_path / "projects")
    monkeypatch.setattr(skill_soul, "SKILL_SOULS_DIR", tmp_path / "skills")
    return tmp_path


# ── Soul dự án ───────────────────────────────────────────────────────────────

def test_bai_hoc_thuong_hieu_vao_soul_du_an(souls):
    from core.project_soul import (append_project_lessons, ensure_project_soul_file,
                                   project_soul_for_prompt)

    ensure_project_soul_file({"id": 1, "name": "Shop len handmade"})
    assert append_project_lessons(1, "Shop len handmade", "Dạy giọng",
                                  ['Gọi khách là "mấy bà", "các mom".']) == 1

    prompt = project_soul_for_prompt(1)
    assert "mấy bà" in prompt
    assert "ĐÈ LÊN" in prompt, "phải nói rõ dự án thắng khuôn mẫu kỹ năng"


def test_du_an_khac_khong_thay_giong_du_an_nay(souls):
    """Đây là điểm mấu chốt của cả tính năng: cùng một nhân viên, cùng một kỹ
    năng, sang dự án khác thì KHÔNG được mang theo giọng của dự án cũ."""
    from core.project_soul import (append_project_lessons, ensure_project_soul_file,
                                   project_soul_for_prompt)

    ensure_project_soul_file({"id": 1, "name": "Shop len"})
    ensure_project_soul_file({"id": 2, "name": "Nội thất gỗ"})
    append_project_lessons(1, "Shop len", "Dạy giọng", ['Gọi khách là "mấy bà".'])

    assert "mấy bà" not in project_soul_for_prompt(2)


def test_du_an_chua_co_gi_thi_khong_nhet_gi_vao_prompt(souls):
    """Khung soul rỗng + câu nêu thứ tự ưu tiên khi chưa có luật nào để ưu tiên
    chỉ tổ nhiễu prompt."""
    from core.project_soul import ensure_project_soul_file, project_soul_for_prompt

    ensure_project_soul_file({"id": 3, "name": "Dự án mới toanh"})
    assert project_soul_for_prompt(3) == ""
    assert project_soul_for_prompt(999) == ""


def test_mo_ta_du_an_dong_bo_lai_khi_papa_sua(souls):
    """Papa sửa mô tả trong tab Dự án thì lần chạy kế tiếp phải thấy bản mới,
    không phải bản chụp lúc tạo file."""
    from core.project_soul import (append_project_lessons, project_soul_for_prompt,
                                   sync_project_brief)

    sync_project_brief({"id": 4, "name": "Shop len", "description": "Bán len móc tay."})
    assert "Bán len móc tay." in project_soul_for_prompt(4)

    append_project_lessons(4, "Shop len", "Buổi 1", ["Giữ bài học này."])
    sync_project_brief({"id": 4, "name": "Shop len", "description": "Bán len VÀ phụ kiện."})

    prompt = project_soul_for_prompt(4)
    assert "Bán len VÀ phụ kiện." in prompt
    assert "Bán len móc tay." not in prompt
    assert "Giữ bài học này." in prompt, "đồng bộ mô tả không được xoá bài học"


def test_hai_buoi_day_cong_don_khong_de_len_nhau(souls):
    from core.project_soul import append_project_lessons, read_project_soul

    append_project_lessons(5, "Shop len", "Buổi 1", ["Bài một."])
    append_project_lessons(5, "Shop len", "Buổi 2", ["Bài hai."])

    text = read_project_soul(5)
    assert "Bài một." in text and "Bài hai." in text


# ── Hai chế độ: làm ra sản phẩm vs nói chuyện ────────────────────────────────
#
# Ca thật: câu "cách bạn nói chuyện với Papa vẫn giữ đúng tính cách riêng" từng
# nằm chung với đoạn nêu thứ tự ưu tiên, nên nó đi vào cả prompt quy trình và là
# dòng CUỐI CÙNG model đọc trước khi viết. Celexa trả về "Sếp, em dùng skill
# imagegen vì lần này cần tạo ảnh đi kèm post..." và cả lời dẫn đó bị lưu nguyên
# văn thành nội dung bài đăng chờ duyệt.

def test_prompt_quy_trinh_khong_nhac_toi_tro_chuyen(souls):
    from core.project_soul import append_project_lessons, project_soul_for_prompt

    append_project_lessons(6, "Shop len", "Buổi 1", ["Gọi khách là mấy bà."])
    prompt = project_soul_for_prompt(6)          # mặc định = chế độ sản phẩm

    assert "ĐÈ LÊN" in prompt
    assert "nói chuyện" not in prompt, "trong quy trình không có ai để nói chuyện"


def test_phong_hop_va_phong_day_van_giu_duoc_tinh_cach(souls):
    """Không có câu này thì luật dự án lấn sang cả cách nhân viên nói chuyện, và
    Celexa mang giọng bán hàng của shop len vào phòng họp."""
    from core.project_soul import append_project_lessons, project_soul_for_prompt

    append_project_lessons(7, "Shop len", "Buổi 1", ["Gọi khách là mấy bà."])
    prompt = project_soul_for_prompt(7, mode="conversation")

    assert "ĐÈ LÊN" in prompt
    assert "nói chuyện" in prompt


def test_luat_cung_cua_quy_trinh_cam_loi_dan():
    """Luật này là dòng cuối trong system prompt của MỌI bước quy trình, kể cả
    bước không gắn dự án — nên nó không được phụ thuộc vào soul dự án."""
    from api.websocket_workflow import _WORKFLOW_OUTPUT_RULE

    assert "KHÔNG PHẢI CUỘC TRÒ CHUYỆN" in _WORKFLOW_OUTPUT_RULE
    assert "lời chào" in _WORKFLOW_OUTPUT_RULE
    assert "em dùng kỹ năng" in _WORKFLOW_OUTPUT_RULE
    # Có bước mà việc phải làm chính là phân tích — cấm luôn thì hỏng bước đó.
    assert "phân tích" in _WORKFLOW_OUTPUT_RULE


# ── Lớp chặn lời dẫn ─────────────────────────────────────────────────────────
#
# Tất cả câu dưới đây là output THẬT của Celexa khi đo lặp, không phải câu bịa ra.
# Đo được: prompt không luật cứng 3/5 lượt dính, có luật cứng vẫn 1/5. Nên phải có
# lớp chặn xác định, không thể chỉ dặn trong prompt.

@pytest.mark.parametrize("text", [
    "Sếp, em dùng skill imagegen vì lần này cần tạo ảnh đi kèm post.",
    'Sếp giao "post và ảnh" nên em xử luôn theo đúng tinh thần fanpage.',
    "Okee, em hiểu rồi, Sếp! Em sẽ research từ khóa trước, rồi viết bài.",
    "Em sẽ phân tích từ khóa trending về túi len, rồi viết luôn bài đăng cho Sếp.",
    "Sẵn sàng! Em sẽ bắt đầu với bước 1 — nghiên cứu từ khóa về túi len.",
    "Để em chạy luôn ahh — đầu tiên research từ khóa, rồi viết post.",
    "\n\n   \nDạ em gửi Sếp bài đăng ạ.",     # lời dẫn sau vài dòng trống
    # Bản dò đầu tiên của tôi lọt đúng ba câu này: "em xin phép" thì bắt được
    # nhưng "em xin lỗi" thì không, và "Được rồi Sếp" / "Em chạy ngay nhé Sếp"
    # cũng không khớp mẫu nào.
    "Em xin lỗi Sếp, để viết bài túi len được xịn xò thì em cần Sếp cung cấp thêm chi tiết.",
    "Được rồi Sếp, em chạy quy trình viết bài về túi len luôn.",
    "Em chạy ngay luôn nhé Sếp! Bắt đầu với nghiên cứu từ khóa trending về túi len.",
    "Em bắt đầu luôn nhé Sếp!",
    "Sếp ơi, em cần hỏi một chút trước khi chạy:",
])
def test_bat_duoc_loi_dan_that(text):
    from api.websocket_workflow import _looks_like_preamble
    assert _looks_like_preamble(text) is True


@pytest.mark.parametrize("text", [
    "Cái túi len này nhìn hiền hiền vậy thôi chứ lên đồ là thấy có chuyện liền á mấy bà 🧶",
    "🔍 NGHIÊN CỨU TỪ KHÓA — TÚI LEN HANDMADE",
    "Túi len mềm mịn, cầm lên là muốn ôm vào luôn 🧶",
    "Móc xong cái túi màu kem này tự nhiên thấy nó hiền khô luôn mấy bà.",
    "Quý khách vui lòng liên hệ chúng tôi để được tư vấn.",
    "Mấy bà thích màu nào hơn?",
    "",
])
def test_khong_bat_nham_bai_dang_that(text):
    """Bắt nhầm thì gọi model lại một lần vô ích, mà lần hai chưa chắc hay bằng."""
    from api.websocket_workflow import _looks_like_preamble
    assert _looks_like_preamble(text) is False


@pytest.fixture
def gia_lap_model(monkeypatch):
    """Thay câu trả lời của model cho các lần xin lại.

    Nhận một chuỗi (mọi lần trả như nhau) hoặc danh sách (lần 1, lần 2...).
    `goi` đếm số lần thật sự gọi model.
    """
    goi = {"n": 0}

    def dat(reply):
        from api import websocket_workflow as ww
        replies = [reply] if isinstance(reply, str) else list(reply)

        async def fake(messages):
            goi["n"] += 1
            return replies[min(goi["n"] - 1, len(replies) - 1)]
        monkeypatch.setattr(ww.hermes, "complete_with_context", fake)
        return goi
    return dat


def _xin_lai(first):
    import asyncio
    from api.websocket_workflow import _retry_without_preamble
    return asyncio.run(_retry_without_preamble([{"role": "user", "content": "x"}], first, []))


BAN_HONG = "Sếp, em gửi bài nè. " + "nội dung dài dài cho đủ độ dài so sánh. " * 4


def test_lan_hai_sach_thi_lay_ban_hai(gia_lap_model):
    sach = "Cái túi len này nhìn hiền hiền. " + "nội dung dài dài cho đủ độ dài. " * 4
    gia_lap_model(sach)
    assert _xin_lai(BAN_HONG) == sach.strip()


def test_lan_hai_hong_thi_con_lan_ba(gia_lap_model):
    """Ca thật: model xin lỗi rồi hỏi lại lần nữa. Một lượt nhắc là không đủ."""
    sach = "Cái túi len này nhìn hiền hiền. " + "nội dung dài dài cho đủ độ dài. " * 4
    goi = gia_lap_model(["Dạ em xin lỗi Sếp, để em hỏi lại ạ.", sach])
    assert _xin_lai(BAN_HONG) == sach.strip()
    assert goi["n"] == 2


def test_het_luot_nhac_van_hong_thi_giu_ban_goc(gia_lap_model):
    """Trả "" = bên gọi giữ nguyên bản đầu. Thà thừa một câu dẫn còn hơn mất bài."""
    goi = gia_lap_model("Dạ em xin lỗi Sếp, em viết lại ạ. " + "nội dung. " * 20)
    assert _xin_lai(BAN_HONG) == ""
    assert goi["n"] == 2, "phải dừng đúng 2 lần, không nhắc mãi"


def test_lan_hai_ngan_hon_han_thi_giu_ban_goc(gia_lap_model):
    """Model hay tưởng chỉ cần sửa mỗi câu đầu rồi trả về mẩu cụt."""
    dai = "Sếp, em gửi bài nè. " + "nội dung dài dài cho đủ ngưỡng so sánh. " * 15
    gia_lap_model("Túi len xinh lắm.")
    assert _xin_lai(dai) == ""


def test_ban_dau_chi_la_cau_hoi_cut_thi_khong_so_do_dai(gia_lap_model):
    """Bản đầu là câu hỏi 70 chữ; mọi bài viết tử tế đều dài hơn nên phép so độ
    dài vô nghĩa ở đây — trước khi sửa, chính luật đó làm hỏng ca này."""
    hoi = "Sếp ơi, em cần hỏi một chút để viết bài chuẩn chứ không phải bịa ạ."
    bai = "Cái túi len này nhìn hiền hiền mấy bà ơi."
    gia_lap_model(bai)
    assert _xin_lai(hoi) == bai


def test_lan_hai_rong_thi_giu_ban_goc(gia_lap_model):
    gia_lap_model("   ")
    assert _xin_lai(BAN_HONG) == ""


# ── Bước gắn nhiều kỹ năng: chỉ giao sản phẩm cuối ───────────────────────────
#
# Ca thật: bước "Celexa · research_keyword_for_post, write_post" trả về báo cáo
# nghiên cứu từ khóa 2.300 chữ rồi mới tới bài đăng 700 chữ. Thẻ duyệt dán nhãn
# "NỘI DUNG BÀI ĐĂNG" nhưng hiện bảng phân tích từ khóa.

def test_cat_bo_phan_chuan_bi_giu_san_pham():
    from api.websocket_workflow import _RESULT_MARKER, _extract_deliverable

    raw = ("🔍 NGHIÊN CỨU TỪ KHÓA — TÚI XÁCH BẰNG LEN\n"
           "| túi xách len handmade | Cao | 📈 |\n\n"
           f"{_RESULT_MARKER}\n"
           "Cái túi len này nhìn hiền hiền vậy thôi mấy bà 🧶\n\n#tuixachlen")
    got = _extract_deliverable(raw)
    assert got.startswith("Cái túi len này")
    assert "NGHIÊN CỨU TỪ KHÓA" not in got


def test_khong_co_dau_moc_thi_giu_nguyen():
    """Model quên đặt mốc mà mình cắt bừa là mất trắng sản phẩm."""
    from api.websocket_workflow import _extract_deliverable

    text = "Cái túi len này nhìn hiền hiền.\n\n---\n\nMỗi bé một kiểu.\n\n#tuilen"
    assert _extract_deliverable(text) == text


def test_dau_gach_ngang_trong_bai_khong_bi_nham_la_moc():
    """Vì sao dùng dấu mốc riêng chứ không cắt theo '---': bài đăng có '---' thật."""
    from api.websocket_workflow import _extract_deliverable

    text = "Phần đầu\n\n---\n\nPhần sau vẫn thuộc về bài đăng"
    assert _extract_deliverable(text) == text


def test_sau_dau_moc_rong_thi_giu_nguyen():
    from api.websocket_workflow import _RESULT_MARKER, _extract_deliverable

    text = f"Bài đăng thật ở đây\n\n{_RESULT_MARKER}\n   \n"
    assert _extract_deliverable(text) == text


def test_moc_xuat_hien_nhieu_lan_thi_lay_lan_cuoi():
    """Model nhắc lại dấu mốc trong phần chuẩn bị — phải lấy lần cuối cùng."""
    from api.websocket_workflow import _RESULT_MARKER, _extract_deliverable

    text = (f"Dàn ý: sẽ kết thúc bằng {_RESULT_MARKER} nhé\n"
            f"{_RESULT_MARKER}\nBài đăng thật")
    assert _extract_deliverable(text) == "Bài đăng thật"


# ── Phụ lục kỹ năng ──────────────────────────────────────────────────────────

def test_bai_hoc_ve_nghe_dung_chung_cho_moi_nguoi(souls):
    from core.skill_soul import append_skill_lessons, skill_soul_for_prompt

    append_skill_lessons(3, "write_post", "Dạy định dạng",
                         ["Caption không dùng markdown."])

    prompt = skill_soul_for_prompt(3, "write_post")
    assert "Caption không dùng markdown." in prompt
    assert "write_post" in prompt
    assert "ĐÈ LÊN" in prompt


def test_ky_nang_chua_duoc_day_thi_khong_them_gi(souls):
    from core.skill_soul import skill_soul_for_prompt

    assert skill_soul_for_prompt(99, "chưa dạy") == ""


def test_phu_luc_khong_dung_vao_noi_dung_ky_nang_papa_viet(souls):
    """Phụ lục nằm ở FILE RIÊNG, không chèn vào skills.config_json — Papa mở tab
    Kỹ năng sửa lại nội dung thì bài học đã dạy vẫn còn."""
    from core.skill_soul import append_skill_lessons, skill_soul_path

    append_skill_lessons(3, "write_post", "Buổi 1", ["Bài học nghề."])
    assert skill_soul_path(3).exists()
    assert "Bài học nghề." in skill_soul_path(3).read_text(encoding="utf-8")


# ── Chia phạm vi lúc Papa duyệt ──────────────────────────────────────────────

def test_the_pham_vi_trong_o_duc_ket_duoc_doc_dung():
    from api.routes.training import _lessons_from_notes

    notes = ("[dự án] Gọi khách là mấy bà\n"
             "[kỹ năng: write_post] Không dùng markdown\n"
             "[nhân viên] Xưng em với Sếp\n"
             "Dòng không gắn thẻ")
    got = _lessons_from_notes(notes)
    assert [(x["scope"], x["text"]) for x in got] == [
        ("project", "Gọi khách là mấy bà"),
        ("skill", "Không dùng markdown"),
        ("agent", "Xưng em với Sếp"),
        ("agent", "Dòng không gắn thẻ"),
    ]
    assert got[1]["skill"] == "write_post"


def test_the_khong_dau_van_doc_duoc():
    """Papa gõ nhanh thì hay rơi dấu — rơi dấu mà mất phạm vi thì ức chế."""
    from api.routes.training import _lessons_from_notes

    got = _lessons_from_notes("[du an] Bài A\n[ky nang] Bài B")
    assert [x["scope"] for x in got] == ["project", "skill"]


def test_the_la_thi_giu_nguyen_ca_dong_lam_noi_dung():
    """"[Quan trọng] Bài A" là chữ Papa viết, không phải thẻ phạm vi — cắt mất
    thì bài học sai nghĩa."""
    from api.routes.training import _lessons_from_notes

    got = _lessons_from_notes("[Quan trọng] Bài A")
    assert got == [{"text": "[Quan trọng] Bài A", "scope": "agent", "skill": ""}]


def test_buoi_khong_gan_du_an_thi_ha_ve_nhan_vien():
    """Model vẫn gán "project" dù prompt đã cấm. Bỏ bài học đi thì Papa mất công
    dạy; hạ về nhân viên thì vẫn còn, chỉ hẹp hơn."""
    from api.routes.training import _normalise_scopes

    lessons = [{"text": "Bài A", "scope": "project", "skill": ""}]
    assert _normalise_scopes(lessons, {"project_id": None}, [])[0]["scope"] == "agent"


def test_pham_vi_ky_nang_khop_ten_de_ra_dung_file():
    from api.routes.training import _normalise_scopes

    skills = [{"id": 3, "name": "write_post"}, {"id": 8, "name": "seo_audit"}]
    lessons = [{"text": "Bài A", "scope": "skill", "skill": "SEO_Audit"}]
    got = _normalise_scopes(lessons, {"project_id": 1}, skills)
    assert got[0]["skill_id"] == 8


def test_mot_ky_nang_duy_nhat_thi_khong_can_ghi_ten():
    from api.routes.training import _normalise_scopes

    lessons = [{"text": "Bài A", "scope": "skill", "skill": ""}]
    got = _normalise_scopes(lessons, {"project_id": 1}, [{"id": 3, "name": "write_post"}])
    assert got[0]["skill_id"] == 3


def test_ten_ky_nang_khong_khop_thi_ha_ve_nhan_vien():
    """Đoán bừa một kỹ năng để ghi vào là ghi nhầm sổ dùng chung cho cả công ty."""
    from api.routes.training import _normalise_scopes

    skills = [{"id": 3, "name": "write_post"}, {"id": 8, "name": "seo_audit"}]
    lessons = [{"text": "Bài A", "scope": "skill", "skill": "kỹ năng nào đó"}]
    assert _normalise_scopes(lessons, {"project_id": 1}, skills)[0]["scope"] == "agent"


def test_duc_ket_hien_ra_kem_the_de_papa_sua():
    from api.routes.training import _tag_lessons

    out = _tag_lessons([
        {"text": "Bài A", "scope": "project", "skill": ""},
        {"text": "Bài B", "scope": "skill", "skill": "write_post"},
        {"text": "Bài C", "scope": "agent", "skill": ""},
    ])
    assert out == ("[dự án] Bài A\n"
                   "[kỹ năng: write_post] Bài B\n"
                   "[nhân viên] Bài C")


def test_the_hien_ra_va_the_doc_lai_khop_nhau():
    """Vòng tròn phải khép: thứ Papa nhìn thấy trên màn hình đúng bằng thứ server
    đọc lại lúc đóng phòng."""
    from api.routes.training import _lessons_from_notes, _tag_lessons

    lessons = [
        {"text": "Bài A", "scope": "project", "skill": ""},
        {"text": "Bài B", "scope": "skill", "skill": "write_post"},
        {"text": "Bài C", "scope": "agent", "skill": ""},
    ]
    got = _lessons_from_notes(_tag_lessons(lessons))
    assert [(x["scope"], x["text"], x["skill"]) for x in got] == [
        ("project", "Bài A", ""),
        ("skill", "Bài B", "write_post"),
        ("agent", "Bài C", ""),
    ]
