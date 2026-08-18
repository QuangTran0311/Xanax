"""Lớp poster phải chạy thuần Pillow, không cần model ảnh hay font cài riêng."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageFont

from core.poster_layer import (
    OFFSET_RANGE,
    SCALE_RANGE,
    build_poster_layout,
    choose_text_color,
    font_supports_vietnamese,
    normalize_poster,
    render_poster_layer,
    resolve_font_family,
    wrap_text,
)


def _noi_dung_day_du():
    return {
        "title": "Chàng Dev Tập Móc",
        "tagline": "Móc từng mũi nhỏ – Gửi trọn yêu thương",
        "features": [
            "100% handmade, móc tay tỉ mỉ",
            "Sợi mềm mại, an toàn cho bé",
            "Quà tặng ý nghĩa mọi dịp",
        ],
        "price": "185.000đ",
        "cta": "Nhắn tin để đặt hàng ngay!",
        "handle": "@chang_dev_tap_moc",
    }


def test_font_fallback_that_su_co_du_dau_tieng_viet():
    """Máy test chỉ cần font hệ thống: Windows dùng Segoe/Arial, Ubuntu dùng DejaVu."""
    family = resolve_font_family()
    assert font_supports_vietnamese(family.regular)
    assert font_supports_vietnamese(family.bold)


def test_tu_xuong_dong_theo_be_rong_pixel():
    family = resolve_font_family()
    font = ImageFont.truetype(family.regular, 28)
    lines = wrap_text("Sợi mềm mại an toàn cho bé và thân thiện làn da", font, 180)
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    assert len(lines) > 1
    assert all(draw.textlength(line, font=font) <= 180 for line in lines)


def test_tu_giam_co_chu_khi_tieu_de_dai():
    content = {"title": "Bộ sưu tập thú bông thủ công dành cho những món quà thật đặc biệt"}
    layout = build_poster_layout((720, 900), content)
    title = layout.top_elements[0]
    co_chu_mac_dinh = int(min(layout.size) * 0.066)
    assert title.font_size < co_chu_mac_dinh
    assert len(title.lines) <= 2


def test_thieu_truong_thi_bo_han_khong_de_cho_trong_hay_placeholder():
    clean = normalize_poster({
        "title": "Mèo Len",
        "tagline": "  ",
        "features": ["Móc tay", "", None],
        "price": None,
        "cta": "Đặt hàng hôm nay",
    })
    assert clean == {
        "title": "Mèo Len",
        "features": ["Móc tay"],
        "cta": "Đặt hàng hôm nay",
    }
    layout = build_poster_layout((720, 900), clean)
    kinds = [item.kind for item in layout.top_elements + layout.bottom_elements]
    assert kinds == ["title", "feature", "cta"]
    assert "price" not in kinds and "tagline" not in kinds and "handle" not in kinds


def test_chon_chu_toi_tren_nen_sang_va_chu_sang_tren_nen_toi():
    box = (0, 0, 200, 100)
    dark_on_light = choose_text_color(Image.new("RGB", (200, 100), "white"), box)
    light_on_dark = choose_text_color(Image.new("RGB", (200, 100), "black"), box)
    assert sum(dark_on_light) < 180
    assert sum(light_on_dark) > 700


def test_layout_tu_tinh_cao_xuong_va_kep_dung_khoang_an_toan():
    layout = build_poster_layout((1080, 1350), _noi_dung_day_du())
    # Bộ nội dung đầy đủ này dành khoảng 50% chiều cao thật giữa hai khối chữ.
    # Ngưỡng 0.48 đủ chặn hồi quy 0.39 (trừ padding/bóng hai lần), nhưng vẫn chừa
    # sai số font hệ thống giữa Windows và Linux.
    assert layout.product_scale > 0.48
    assert OFFSET_RANGE[0] <= layout.product_y_offset <= OFFSET_RANGE[1]
    assert layout.top_box[3] < layout.bottom_box[1]
    slot_center = (layout.top_box[3] + layout.bottom_box[1]) / 2
    product_center = (0.5 + layout.product_y_offset) * layout.size[1]
    assert abs(product_center - slot_center) <= 1

    # Khung cực thấp cố tình ép chữ quá tải: món hàng vẫn không được nhỏ hơn 30%.
    cramped = build_poster_layout((320, 100), _noi_dung_day_du())
    assert cramped.product_scale == SCALE_RANGE[0]
    assert OFFSET_RANGE[0] <= cramped.product_y_offset <= OFFSET_RANGE[1]


def test_chip_om_sat_chu_va_moi_khoi_dung_chung_content_width():
    layout = build_poster_layout((1080, 1350), _noi_dung_day_du())
    assert layout.top_box[2] - layout.top_box[0] == layout.content_width
    assert layout.bottom_box[2] - layout.bottom_box[0] == layout.content_width
    assert all(
        element.box_width <= layout.content_width
        for element in layout.top_elements + layout.bottom_elements
    )

    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    chip_padding = max(6, int(min(layout.size) * 0.010))
    for feature in (item for item in layout.bottom_elements if item.kind == "feature"):
        font = ImageFont.truetype(layout.font_family.regular, feature.font_size)
        text_width = max(draw.textlength(line, font=font) for line in feature.lines)
        # Sáu padding gồm chỗ cho bullet bên trái và khoảng thở bên phải.
        assert feature.box_width == min(
            layout.content_width, math.ceil(text_width) + chip_padding * 6)
        assert feature.box_width < layout.content_width


def test_vi_tri_khai_bao_tuong_minh_thang_tinh_toan_tu_dong_va_van_duoc_kep():
    content = _noi_dung_day_du()
    automatic = build_poster_layout((1080, 1350), content)
    explicit = build_poster_layout(
        (1080, 1350), content, explicit_placement=(0.55, 0.10))
    assert (explicit.product_scale, explicit.product_y_offset) == (0.55, 0.10)
    assert (explicit.product_scale, explicit.product_y_offset) != (
        automatic.product_scale, automatic.product_y_offset)

    clipped = build_poster_layout(
        (1080, 1350), content, explicit_placement=(9, -9))
    assert (clipped.product_scale, clipped.product_y_offset) == (0.90, -0.15)


def test_ve_lop_poster_thay_doi_anh_va_giu_nguyen_kich_thuoc():
    content = _noi_dung_day_du()
    source = Image.new("RGB", (720, 900), (235, 226, 210))
    layout = build_poster_layout(source.size, content)
    result = render_poster_layer(source, layout)
    assert result.mode == "RGB"
    assert result.size == source.size
    assert result.tobytes() != source.tobytes()


async def test_luong_che_do_b_ghep_san_pham_roi_moi_ve_poster(tmp_path, monkeypatch):
    """Test đúng seam production nhưng thay model ảnh bằng nền PIL chạy offline."""
    from core import image_gen, model_pool_bridge
    from hub import database

    product = Image.new("RGBA", (140, 360), (0, 0, 0, 0))
    ImageDraw.Draw(product).rounded_rectangle((20, 10, 120, 350), radius=20,
                                               fill=(210, 42, 42, 255))
    product_path = tmp_path / "san-pham.png"
    output_path = tmp_path / "poster.png"
    product.save(product_path)

    async def fake_entries(_ids):
        yield {
            "id": 7, "name": "Model test", "model_id": "offline",
            "base_url": "http://offline", "api_key": "x", "api_style": "",
        }

    async def fake_generate(**kwargs):
        Image.new("RGB", (720, 900), (238, 230, 214)).save(kwargs["save_path"])
        return kwargs["save_path"]

    async def fake_record(*_args):
        return None

    monkeypatch.setattr(model_pool_bridge, "iter_usable_pool_entries", fake_entries)
    monkeypatch.setattr(image_gen, "generate_image", fake_generate)
    monkeypatch.setattr(database, "record_model_usage", fake_record)
    monkeypatch.setattr(database, "record_model_usage_hourly", fake_record)
    monkeypatch.setattr(database, "record_model_call_log", fake_record)

    err = await image_gen.generate_with_agent_models(
        prompt="empty background, no text", ratio=(4, 5), model_pool_ids=[7],
        save_path=output_path, product_overlay=product_path, poster=_noi_dung_day_du(),
    )
    assert err is None
    result = Image.open(output_path).convert("RGB")
    assert result.size == (720, 900)
    pixels = result.load()
    assert any(
        pixels[x, y][0] > 170 and pixels[x, y][1] < 90
        for y in range(result.height) for x in range(result.width)
    ), \
        "sản phẩm đỏ phải còn trong ảnh sau khi vẽ poster"
    assert result.tobytes() != Image.new("RGB", result.size, (238, 230, 214)).tobytes()


async def _dung_poster_qua_pipeline_that(
    tmp_path, monkeypatch, *, dark_background: bool,
):
    """Thay đúng bước gọi model bằng nền PIL; ghép và render vẫn là production."""
    from core import image_gen, model_pool_bridge, poster_layer
    from hub import database

    product_color = (150, 110, 78)
    product = Image.new("RGBA", (600, 700), (*product_color, 255))
    product_path = tmp_path / "san-pham-nau.png"
    output_path = tmp_path / ("poster-toi.png" if dark_background else "poster-kem.png")
    product.save(product_path)

    async def fake_entries(_ids):
        yield {
            "id": 9, "name": "Model nền offline", "model_id": "offline",
            "base_url": "http://offline", "api_key": "x", "api_style": "",
        }

    async def fake_generate(**kwargs):
        if dark_background:
            background = Image.new("RGB", (1080, 1350), (42, 42, 42))
        else:
            background = Image.new("RGB", (1080, 1350))
            draw = ImageDraw.Draw(background)
            for y in range(background.height):
                position = y / (background.height - 1)
                color = tuple(round(start + (end - start) * position) for start, end in zip(
                    (245, 239, 227), (227, 217, 197)))
                draw.line((0, y, background.width, y), fill=color)
        background.save(kwargs["save_path"])
        return kwargs["save_path"]

    async def fake_record(*_args):
        return None

    decisions = []
    panels = []
    original_choose = poster_layer._choose_text_treatment
    original_panel = poster_layer._draw_soft_panel

    def record_choose(image, box, palette):
        decision = original_choose(image, box, palette)
        decisions.append((box, decision))
        return decision

    def record_panel(image, box, fill, alpha):
        panels.append((box, fill, alpha))
        return original_panel(image, box, fill, alpha)

    monkeypatch.setattr(model_pool_bridge, "iter_usable_pool_entries", fake_entries)
    monkeypatch.setattr(image_gen, "generate_image", fake_generate)
    monkeypatch.setattr(database, "record_model_usage", fake_record)
    monkeypatch.setattr(database, "record_model_usage_hourly", fake_record)
    monkeypatch.setattr(database, "record_model_call_log", fake_record)
    monkeypatch.setattr(poster_layer, "_choose_text_treatment", record_choose)
    monkeypatch.setattr(poster_layer, "_draw_soft_panel", record_panel)

    err = await image_gen.generate_with_agent_models(
        prompt="empty background, no text", ratio=(4, 5), model_pool_ids=[9],
        save_path=output_path, product_overlay=product_path, poster=_noi_dung_day_du(),
    )
    assert err is None
    return Image.open(output_path).convert("RGB"), decisions, panels, product_color


def _co_mau_san_pham_trong_vung(image, box, product_color):
    region = image.crop(box)
    pixels = region.load()
    return any(
        all(abs(pixels[x, y][channel] - product_color[channel]) <= 2 for channel in range(3))
        for y in range(region.height)
        for x in range(region.width)
    )


async def test_nen_kem_co_san_pham_nau_lot_vao_khung_nhung_khong_co_panel(
    tmp_path, monkeypatch,
):
    """Hồi quy lỗi: mép sản phẩm trong block không được đại diện cho nền dưới chữ."""
    result, decisions, panels, product_color = await _dung_poster_qua_pipeline_that(
        tmp_path, monkeypatch, dark_background=False)
    layout = build_poster_layout(result.size, _noi_dung_day_du())

    assert _co_mau_san_pham_trong_vung(result, layout.top_box, product_color)
    assert _co_mau_san_pham_trong_vung(result, layout.bottom_box, product_color)
    assert panels == []
    assert decisions and all(sum(decision.text_color) < 180 for _box, decision in decisions)


async def test_nen_xam_than_tu_doi_sang_chu_va_khong_lam_dung_panel(
    tmp_path, monkeypatch,
):
    result, decisions, panels, _product_color = await _dung_poster_qua_pipeline_that(
        tmp_path, monkeypatch, dark_background=True)

    assert result.size == (1080, 1350)
    assert panels == []
    assert decisions and all(sum(decision.text_color) > 700 for _box, decision in decisions)


def test_panel_khi_can_lay_tong_nen_tai_cho_va_chi_om_bbox_dong():
    """Nền chắp sáng/tối nặng mới cần panel; fill phải giữ sắc nâu ấm tại chỗ."""
    from core import poster_layer

    image = Image.new("RGB", (240, 80), (55, 35, 20))
    ImageDraw.Draw(image).rectangle((120, 0, 239, 79), fill=(235, 205, 160))
    palette = poster_layer.make_palette()
    line_box = (70, 20, 170, 55)
    treatment = poster_layer._choose_text_treatment(image, line_box, palette)

    assert treatment.mode == "panel"
    assert treatment.panel_fill is not None
    assert treatment.panel_fill[0] > treatment.panel_fill[1] > treatment.panel_fill[2]
    expanded = poster_layer._expanded_line_box(line_box, image.size, 28)
    assert expanded[2] - expanded[0] < image.width
