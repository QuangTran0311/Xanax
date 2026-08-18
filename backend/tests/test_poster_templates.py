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


def test_thuoc_do_phan_biet_nen_trong_voi_vung_bi_ve_vat_the():
    template = get_template("giua-khung")
    size = (600, 750)
    blank = Image.new("RGB", size)
    draw = ImageDraw.Draw(blank)
    for y in range(size[1]):
        shade = 238 - round(10 * y / size[1])
        draw.line((0, y, size[0], y), fill=(shade, shade - 5, shade - 12))

    occupied = blank.copy()
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

    clean_measure = measure_empty_product_region(blank, r)
    occupied_measure = measure_empty_product_region(occupied, r)
    assert clean_measure.empty, clean_measure.log_summary()
    assert not occupied_measure.empty, occupied_measure.log_summary()
    assert occupied_measure.edge_density > clean_measure.edge_density
    assert occupied_measure.color_stddev > clean_measure.color_stddev


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
            ImageDraw.Draw(canvas).rectangle(
                (round(r.left * 600), round(r.top * 750),
                 round(r.right * 600), round(r.bottom * 750)),
                fill=(25, 75, 180),
            )
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
    result = Image.open(output_path).convert("RGB")
    assert any(
        result.getpixel((x, y))[0] > 170 and result.getpixel((x, y))[1] < 80
        for y in range(result.height) for x in range(result.width)
    ), "lần hai vẫn phải được ghép ảnh sản phẩm thật"
