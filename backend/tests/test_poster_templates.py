"""Template poster, phép đặt ảnh thật và cổng kiểm tra vùng chừa."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw

from core.image_compose import compose_on_background
from core.image_gen import extract_template_code
from core.poster_background import measure_empty_product_region
from core.poster_templates import DEFAULT_TEMPLATE_CODE, get_template


def test_tra_template_theo_ma_va_ma_la_lui_ve_mac_dinh():
    assert get_template("trai-san-pham").code == "trai-san-pham"
    assert get_template("khong-ton-tai").code == DEFAULT_TEMPLATE_CODE
    assert get_template(None).code == DEFAULT_TEMPLATE_CODE
    assert extract_template_code("TEMPLATE\nluoi-the-duoi") == "luoi-the-duoi"
    assert extract_template_code("TEMPLATE: ma-la") == DEFAULT_TEMPLATE_CODE


def test_san_pham_vua_khit_vung_giu_ty_le_canh_ngang_va_canh_day(tmp_path):
    product = Image.new("RGBA", (120, 240), (220, 40, 40, 255))
    product_path = tmp_path / "san-pham.png"
    background_path = tmp_path / "nen.png"
    output_path = tmp_path / "poster.png"
    product.save(product_path)
    Image.new("RGB", (1000, 1250), (240, 232, 220)).save(background_path)

    template = get_template("giua-khung")
    compose_on_background(
        product_path, background_path, output_path, shadow=False,
        product_region=template.product_region,
    )

    result = Image.open(output_path).convert("RGB")
    red = [
        (x, y) for y in range(result.height) for x in range(result.width)
        if result.getpixel((x, y))[0] > 170 and result.getpixel((x, y))[1] < 90
    ]
    left, top = min(x for x, _ in red), min(y for _, y in red)
    right, bottom = max(x for x, _ in red), max(y for _, y in red)
    width, height = right - left + 1, bottom - top + 1
    region = template.product_region
    expected_center = (region.left + region.right) * result.width / 2
    expected_bottom = round(region.bottom * result.height) - 1

    assert abs(width / height - 0.5) < 0.02, "không được bóp méo tỷ lệ sản phẩm"
    assert abs((left + right) / 2 - expected_center) <= 2, "phải canh ngang giữa ô"
    assert abs(bottom - expected_bottom) <= 2, "mép dưới phải sát đáy vùng sản phẩm"
    assert left >= round(region.left * result.width)
    assert right < round(region.right * result.width)
    assert top >= round(region.top * result.height)


def _tao_nen_lien_mach(size=(600, 750)):
    """Gradient tường và mặt bàn đều chạy hết chiều ngang, kể cả qua vùng sản phẩm."""
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    mat_ban_y = round(size[1] * 0.70)
    for y in range(size[1]):
        if y < mat_ban_y:
            shade = 240 - round(10 * y / size[1])
            color = (shade, shade - 5, shade - 12)
        else:
            depth = y - mat_ban_y
            color = (218 - depth // 35, 203 - depth // 42, 181 - depth // 50)
        draw.line((0, y, size[0], y), fill=color)
    return image


def _hop_pixel(region, size=(600, 750)):
    return (
        round(region.left * size[0]), round(region.top * size[1]),
        round(region.right * size[0]), round(region.bottom * size[1]),
    )


def _ve_vien_dut_net(draw, box, color=(230, 105, 25), width=5):
    left, top, right, bottom = box
    for x in range(left, right, 22):
        draw.line((x, top, min(x + 13, right), top), fill=color, width=width)
        draw.line((x, bottom, min(x + 13, right), bottom), fill=color, width=width)
    for y in range(top, bottom, 22):
        draw.line((left, y, left, min(y + 13, bottom)), fill=color, width=width)
        draw.line((right, y, right, min(y + 13, bottom)), fill=color, width=width)


def test_thuoc_do_cho_nen_gradient_va_mat_ban_lien_mach_di_qua():
    region = get_template("giua-khung").product_region
    measurement = measure_empty_product_region(_tao_nen_lien_mach(), region)

    assert measurement.empty, measurement.log_summary()
    assert not measurement.boundary_violation
    assert not measurement.flat_panel_violation
    assert not measurement.content_violation


def test_thuoc_do_loai_panel_phang_co_vien_dut_net_dung_vung_san_pham():
    region = get_template("giua-khung").product_region
    image = _tao_nen_lien_mach()
    box = _hop_pixel(region)
    draw = ImageDraw.Draw(image)
    draw.rectangle(box, fill=(250, 231, 188))
    _ve_vien_dut_net(draw, box)

    measurement = measure_empty_product_region(image, region)

    assert not measurement.empty, measurement.log_summary()
    assert measurement.boundary_violation, measurement.log_summary()


def test_thuoc_do_loai_panel_phang_khong_co_vien():
    region = get_template("giua-khung").product_region
    image = _tao_nen_lien_mach()
    ImageDraw.Draw(image).rectangle(_hop_pixel(region), fill=(250, 225, 170))

    measurement = measure_empty_product_region(image, region)

    assert not measurement.empty, measurement.log_summary()
    assert measurement.flat_panel_violation, measurement.log_summary()


def test_thuoc_do_giu_hanh_vi_loai_vat_the_co_chi_tiet_trong_vung():
    template = get_template("giua-khung")
    size = (600, 750)
    occupied = _tao_nen_lien_mach(size)
    r = template.product_region
    box = (
        round((r.left + 0.05) * size[0]), round((r.top + 0.04) * size[1]),
        round((r.right - 0.05) * size[0]), round((r.bottom - 0.04) * size[1]),
    )
    draw = ImageDraw.Draw(occupied)
    draw.rounded_rectangle(box, radius=35, fill=(30, 80, 170), outline=(250, 180, 40), width=10)
    for offset in range(20, box[2] - box[0], 24):
        draw.line((box[0] + offset, box[1] + 10, box[0] + offset, box[3] - 10),
                  fill=(245, 225, 180), width=5)

    occupied_measure = measure_empty_product_region(occupied, r)

    assert not occupied_measure.empty, occupied_measure.log_summary()
    assert occupied_measure.content_violation, occupied_measure.log_summary()


async def test_pipeline_sinh_lai_dung_mot_lan_khi_vung_chua_bi_chiem(tmp_path, monkeypatch):
    """Lần hai đạt thì dùng nền mới rồi ghép, không gọi model lần thứ ba."""
    from core import image_gen, model_pool_bridge
    from hub import database

    product_path = tmp_path / "sp.png"
    Image.new("RGBA", (80, 220), (210, 30, 30, 255)).save(product_path)
    output_path = tmp_path / "poster.png"
    calls = []

    async def fake_entries(_ids):
        yield {
            "id": 7, "name": "Model giả", "model_id": "offline",
            "base_url": "http://offline", "api_key": "x", "api_style": "",
        }

    async def fake_generate(**kwargs):
        calls.append(kwargs["prompt"])
        canvas = Image.new("RGB", (600, 750), (238, 232, 220))
        if len(calls) == 1:
            r = get_template("giua-khung").product_region
            box = _hop_pixel(r)
            draw = ImageDraw.Draw(canvas)
            draw.rectangle(box, fill=(250, 225, 170))
            _ve_vien_dut_net(draw, box)
        canvas.save(kwargs["save_path"])
        return kwargs["save_path"]

    async def fake_record(*_args):
        return None

    monkeypatch.setattr(model_pool_bridge, "iter_usable_pool_entries", fake_entries)
    monkeypatch.setattr(image_gen, "generate_image", fake_generate)
    monkeypatch.setattr(database, "record_model_usage", fake_record)
    monkeypatch.setattr(database, "record_model_usage_hourly", fake_record)
    monkeypatch.setattr(database, "record_model_call_log", fake_record)

    error = await image_gen.generate_with_agent_models(
        prompt="Design a poster and reserve the product rectangle",
        ratio=(4, 5), model_pool_ids=[7], save_path=output_path,
        product_overlay=product_path, template_code="giua-khung",
        composition_mode="template",
    )

    assert error is None
    assert len(calls) == 2
    assert "CRITICAL RETRY CORRECTION" in calls[1]
    assert "x=30% to 70%" in calls[1]
    assert "edges concentrated on the exact rectangular boundary" in calls[1]
    assert "abrupt local color jump" in calls[1]
    assert "wall/table junction" in calls[1]
    assert "y=70%" in calls[1]
    result = Image.open(output_path).convert("RGB")
    assert any(
        result.getpixel((x, y))[0] > 170 and result.getpixel((x, y))[1] < 80
        for y in range(result.height) for x in range(result.width)
    ), "lần hai vẫn phải được ghép ảnh sản phẩm thật"
