"""Chọn chế độ A hay B theo việc người dùng có gửi ảnh hay không.

Người dùng phổ thông không biết "chế độ B", không biết đường dẫn, không biết
phải cắt nền trước. Nên việc chọn chế độ phải do máy quyết theo dữ kiện có thật,
rồi nói thẳng cho nhân viên — không để nhân viên tự suy từ lời người dùng.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.image_gen import attached_image_paths, latest_attached_images, photo_mode_note

ANH = r"D:\xanax\data\assets\ab12_ostrich.jpg"

KHOI = (
    "làm cho tôi tấm ảnh đăng bán\n\n"
    "<!-- FILE PAPA GỬI KÈM — đường dẫn tuyệt đối, dùng cho công cụ:\n"
    f"- ostrich.jpg → {ANH}\n"
    "-->\n\n"
    "![ostrich.jpg](/api/assets/9/download)"
)


def test_boc_duoc_duong_dan_anh_dinh_kem():
    assert attached_image_paths(KHOI) == [ANH]
    assert attached_image_paths("chỉ là tin nhắn thường") == []


def test_bo_qua_file_khong_phai_anh():
    """Papa gửi kèm file PDF báo giá thì không được coi là ảnh sản phẩm."""
    text = ("<!-- FILE PAPA GỬI KÈM — đường dẫn tuyệt đối, dùng cho công cụ:\n"
            r"- banggia.pdf → D:\xanax\data\assets\x_banggia.pdf" "\n"
            r"- so.jpg → D:\xanax\data\assets\x_so.jpg" "\n-->")
    assert attached_image_paths(text) == [r"D:\xanax\data\assets\x_so.jpg"]


def test_anh_gui_o_tin_truoc_van_con_hieu_luc():
    """Papa gửi ảnh, tin sau mới nói muốn gì — chỉ nhìn tin cuối là mất ảnh."""
    history = [
        {"role": "user", "content": KHOI},
        {"role": "assistant", "content": "Dạ con thấy ảnh rồi."},
        {"role": "user", "content": "giờ làm poster đi"},
    ]
    assert latest_attached_images(history) == [ANH]


def test_lay_lan_gui_gan_nhat_khong_gop_tat_ca():
    """Làm xong món A, Papa gửi ảnh món B — gộp lại thì bài mang ảnh cả hai món."""
    sau = KHOI.replace("ab12_ostrich.jpg", "cd34_gau.jpg")
    history = [
        {"role": "user", "content": KHOI},
        {"role": "assistant", "content": "xong món thứ nhất"},
        {"role": "user", "content": sau},
    ]
    assert latest_attached_images(history) == [r"D:\xanax\data\assets\cd34_gau.jpg"]


def test_khong_co_anh_thi_chot_che_do_A():
    note = photo_mode_note([])
    assert "CHẾ ĐỘ A" in note
    assert "KHÔNG được bịa ra khối ẢNH SẢN PHẨM" in note


def test_co_anh_thi_chot_che_do_B_va_cam_hoi_lai():
    note = photo_mode_note([ANH])
    assert "CHẾ ĐỘ B" in note
    assert "ab12_ostrich.jpg" in note, "phải đưa thẳng đường dẫn cho nhân viên"
    assert "không hỏi lại" in note
