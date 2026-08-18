"""Ghép ảnh sản phẩm thật lên nền do model vẽ.

Hai bộ sinh ảnh đang dùng đều là text-to-image thuần, không nhận ảnh đầu vào —
nên không thể bảo model "vẽ đúng món hàng này". Cách duy nhất để ảnh đăng bán
mang đúng hàng thật là: model vẽ NỀN, còn sản phẩm là ảnh chụp đã tách nền, dán
lên bằng PIL.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from core.image_compose import compose_on_background
from core.image_gen import (
    extract_image_prompt, extract_image_ratio, extract_poster, extract_product_image,
    extract_product_placement, safe_product_path,
)


def _product(tmp: Path, size=(200, 400)) -> Path:
    """Sản phẩm giả: hình chữ nhật đỏ đặc, quanh là viền trong suốt thừa."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(60, 140):
        for y in range(100, 300):
            img.putpixel((x, y), (220, 40, 40, 255))
    p = tmp / "sp.png"
    img.save(p)
    return p


def _background(tmp: Path, size=(1080, 1350)) -> Path:
    p = tmp / "nen.png"
    Image.new("RGB", size, (240, 232, 220)).save(p)
    return p


def test_ghep_dung_ty_le_va_dung_giua(tmp_path):
    out = compose_on_background(
        _product(tmp_path), _background(tmp_path), tmp_path / "ket-qua.png")
    im = Image.open(out).convert("RGB")
    assert im.size == (1080, 1350), "phải giữ nguyên khung của nền"

    # Sản phẩm nằm giữa theo chiều ngang: cột giữa phải có màu đỏ.
    w, h = im.size
    mid_col = [im.getpixel((w // 2, y)) for y in range(h)]
    assert any(p[0] > 150 and p[1] < 100 for p in mid_col), "không thấy sản phẩm ở cột giữa"

    # Bốn góc vẫn là nền — sản phẩm không được phủ kín khung.
    for xy in ((5, 5), (w - 5, 5), (5, h - 5), (w - 5, h - 5)):
        r, g, b = im.getpixel(xy)
        assert (r, g, b) == (240, 232, 220), f"góc {xy} bị đè mất nền"


def test_cat_sat_vien_trong_suot_thua_truoc_khi_tinh_ty_le(tmp_path):
    """Ảnh vào còn viền rỗng mà không cắt thì sản phẩm bị thu bé lại."""
    out = compose_on_background(
        _product(tmp_path), _background(tmp_path), tmp_path / "kq.png", shadow=False)
    im = Image.open(out).convert("RGB")
    w, h = im.size
    reds = [y for y in range(h) if im.getpixel((w // 2, y))[0] > 150]
    # Phần đặc của sản phẩm cao 200/400 ảnh gốc; sau khi cắt sát, chiều cao đó
    # phải chiếm ~68% chiều cao nền, không phải 34%.
    assert (max(reds) - min(reds)) > h * 0.6


def test_bong_do_khong_de_len_san_pham(tmp_path):
    have = compose_on_background(
        _product(tmp_path), _background(tmp_path), tmp_path / "co-bong.png", shadow=True)
    none = compose_on_background(
        _product(tmp_path), _background(tmp_path), tmp_path / "khong-bong.png", shadow=False)
    a, b = Image.open(have).convert("RGB"), Image.open(none).convert("RGB")
    assert a.tobytes() != b.tobytes(), "bật bóng mà ảnh y hệt"
    w, h = a.size
    # Chính giữa sản phẩm vẫn phải là màu sản phẩm, bóng chỉ nằm quanh viền.
    assert a.getpixel((w // 2, h // 2))[0] > 150


def test_xoa_vet_alpha_mo_cua_rembg(tmp_path):
    """rembg để lại cả vạn pixel alpha 1–11 — tàn dư của nền ảnh chụp gốc.

    Trên nền trắng của trình xem ảnh thì không thấy, nhưng dán lên nền màu là hiện
    ra một mảng chữ nhật sáng hơn đúng bằng khung ảnh gốc. Đo trên ảnh con đà điểu
    thật: 20.895 pixel như vậy.
    """
    img = Image.new("RGBA", (200, 400), (255, 255, 255, 5))   # cả tấm là vệt mờ
    for x in range(60, 140):
        for y in range(100, 300):
            img.putpixel((x, y), (220, 40, 40, 255))
    p = tmp_path / "sp-co-vet.png"
    img.save(p)

    out = compose_on_background(
        p, _background(tmp_path), tmp_path / "kq.png", shadow=False)
    im = Image.open(out).convert("RGB")
    w, h = im.size
    # Ngay bên trái sản phẩm (nơi trước đây vệt mờ phủ) phải là nền nguyên chất.
    assert im.getpixel((int(w * 0.12), h // 2)) == (240, 232, 220)
    assert im.getpixel((int(w * 0.88), h // 2)) == (240, 232, 220)


def test_khu_mau_nen_cu_dinh_o_vien(tmp_path):
    """Vành bán trong suốt của rembg vẫn mang màu nền ảnh chụp gốc.

    Đo trên ảnh con đà điểu chụp trên ba lô tối màu: 46.779 pixel biên, độ sáng
    trung bình 41.8 trong khi ruột sản phẩm 156.7 — càng trong suốt càng tối,
    đúng dạng `quan sát = màu_thật × alpha + nền_cũ × (1 − alpha)`. Dán lên nền
    kem là hiện thành đường viền tối quanh sản phẩm.
    """
    from core.image_compose import decontaminate_edge

    # Ruột đỏ đặc; vành alpha 128 mang đúng một nửa màu đỏ (nền cũ là đen).
    img = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    for x in range(10, 50):
        for y in range(10, 50):
            edge = x in (10, 11, 48, 49) or y in (10, 11, 48, 49)
            img.putpixel((x, y), (110, 20, 20, 128) if edge else (220, 40, 40, 255))

    cleaned = decontaminate_edge(img)
    rim = [cleaned.getpixel((x, 30)) for x in (10, 11)]
    assert all(p[0] > 180 for p in rim), f"viền vẫn tối sau khi khử: {rim}"


def test_bong_do_phai_lan_ra_ngoai_khung_san_pham(tmp_path):
    """Bóng phải toả ra vùng nền quanh sản phẩm rồi mới tắt dần.

    Trước đây hình bóng được làm mờ trên tấm canvas chỉ to bằng sản phẩm, nên
    vầng mờ lan tới mép tấm là bị xén cụt: bên ngoài khung sản phẩm không còn
    một chút bóng nào. Kết quả là một khung chữ nhật tối sắc cạnh đúng bằng
    khung sản phẩm — nhìn như dán miếng ảnh lên nền.
    """
    out = compose_on_background(
        _product(tmp_path), _background(tmp_path), tmp_path / "kq.png", shadow=True)
    im = Image.open(out).convert("RGB")
    w, h = im.size
    nen = 240   # kênh đỏ của nền nguyên chất, xem _background

    # Tìm mép trái sản phẩm trên hàng giữa.
    hang = h // 2
    trai = next(x for x in range(w) if im.getpixel((x, hang))[0] > 150
                and im.getpixel((x, hang))[1] < 100)

    ke_ben = im.getpixel((trai - 6, hang))[0]
    xa = im.getpixel((trai - 120, hang))[0]
    assert ke_ben < nen - 15, f"ngay cạnh sản phẩm không có bóng ({ke_ben}) — bóng bị xén theo khung"
    assert xa >= nen - 2, f"ra xa rồi mà vẫn còn bóng ({xa}) — bóng lan quá rộng"


def test_khong_khu_hai_lan_khi_vien_da_sach(tmp_path):
    """Ảnh đã qua alpha_matting thì màu vành đã gỡ khỏi nền sẵn rồi.

    `cut_product` giờ bật alpha_matting mặc định, mà matting của rembg gọi
    `estimate_foreground_ml` — trả về đúng màu sản phẩm, không còn lẫn màu nền.
    Chia ngược alpha lần nữa lên tấm đó là đẩy vành sáng vọt (220 → chạm trần
    255), len trắng ngả bạc. Nên phải tự đo mà bỏ qua.
    """
    from core.image_compose import decontaminate_edge

    # Vành alpha 128 nhưng MÀU đã đúng bằng màu ruột — dấu hiệu đã khử sẵn.
    img = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    for x in range(10, 50):
        for y in range(10, 50):
            edge = x in (10, 11, 48, 49) or y in (10, 11, 48, 49)
            img.putpixel((x, y), (220, 40, 40, 128 if edge else 255))

    cleaned = decontaminate_edge(img)
    rim = cleaned.getpixel((11, 30))
    assert rim[0] == 220, f"vành bị khử lần hai, đỏ vọt lên {rim[0]} thay vì giữ 220"


def test_doc_khoi_anh_san_pham():
    text = ("IMAGE PROMPT\nA warm cream studio backdrop\n\nTỶ LỆ\n4:5\n\n"
            "ẢNH SẢN PHẨM\nD:\\xanax\\data\\assets\\abc_cut.png")
    assert extract_product_image(text) == "D:\\xanax\\data\\assets\\abc_cut.png"
    # Khối mới không được nuốt mất prompt hay tỷ lệ.
    assert extract_image_prompt(text).strip() == "A warm cream studio backdrop"
    assert extract_image_ratio(text) == (4, 5)
    assert extract_product_image("IMAGE PROMPT\nchi co nen\n\nTỶ LỆ\n4:5") is None


def test_doc_khoi_vi_tri_san_pham():
    """Nhân viên tự quyết kích thước và vị trí món hàng trên nền."""
    from core.image_compose import default_placement

    text = ("IMAGE PROMPT\nnen kem\n\nTỶ LỆ\n4:5\n\nẢNH SẢN PHẨM\nD:\\a.png\n\n"
            "VỊ TRÍ SẢN PHẨM\ncao: 0.72\nxuống: 0.02")
    assert extract_product_placement(text) == (0.72, 0.02)

    # Không khai báo thì để compose_on_background tự dùng mặc định của nó.
    assert extract_product_placement("IMAGE PROMPT\nx\n\nTỶ LỆ\n4:5") is None

    # Khai báo nửa vời: thiếu dòng nào thì dòng đó lấy mặc định.
    assert extract_product_placement("VỊ TRÍ SẢN PHẨM\ncao: 0.5") == (0.5, default_placement()[1])

    # Model hay viết phần trăm, viết tiếng Anh, hoặc dùng dấu '='.
    assert extract_product_placement("PRODUCT PLACEMENT\nheight = 60%\noffset: -0.03") == (0.6, -0.03)


def test_doc_khoi_poster_json_dung_chung_ten_truong():
    text = '''IMAGE PROMPT
an empty background without text

TỶ LỆ
4:5

POSTER
```json
{
  "title": "Chàng Dev Tập Móc",
  "tagline": "Gửi trọn yêu thương",
  "features": ["Móc tay tỉ mỉ", "An toàn cho bé", "Quà tặng ý nghĩa", "bị cắt"],
  "price": "299.000₫",
  "cta": "Nhắn tin đặt hàng",
  "handle": "@chang_dev_tap_moc"
}
```'''
    poster = extract_poster(text)
    assert set(poster) == {"title", "tagline", "features", "price", "cta", "handle"}
    assert poster["features"] == ["Móc tay tỉ mỉ", "An toàn cho bé", "Quà tặng ý nghĩa"]
    assert extract_image_prompt(text) == "an empty background without text"
    assert extract_poster("IMAGE PROMPT\nx") is None
    assert extract_poster("POSTER\n{JSON hỏng}") is None


def test_kep_vi_tri_san_pham_ve_khoang_an_toan():
    """Số do model sinh ra — tin thẳng thì món hàng bay ra ngoài khung.

    `cao: 3` sẽ phóng sản phẩm to gấp ba tấm nền; `xuống: 0.9` đẩy nó rơi hẳn
    xuống dưới mép ảnh. Ảnh hỏng mà không ai biết vì sao, vì không có chỗ nào
    báo lỗi. Kẹp lại thì tệ nhất chỉ là bố cục hơi lệch ý.
    """
    qua_to = extract_product_placement("VỊ TRÍ SẢN PHẨM\ncao: 3\nxuống: 0.9")
    assert qua_to == (0.90, 0.15), qua_to
    qua_be = extract_product_placement("VỊ TRÍ SẢN PHẨM\ncao: 0.01\nxuống: -5")
    assert qua_be == (0.30, -0.15), qua_be


def test_chi_nhan_anh_trong_thu_muc_data(tmp_path):
    """Đường dẫn do model sinh ra — không chặn là nó trỏ được vào file bất kỳ."""
    data = tmp_path / "data"
    (data / "assets").mkdir(parents=True)
    inside = data / "assets" / "ok.png"
    inside.write_bytes(b"x")
    outside = tmp_path / "rieng-tu.png"
    outside.write_bytes(b"x")

    assert safe_product_path(str(inside), data) == inside.resolve()
    assert safe_product_path(str(outside), data) is None
    assert safe_product_path(str(data / "khong-co.png"), data) is None
    assert safe_product_path(None, data) is None
