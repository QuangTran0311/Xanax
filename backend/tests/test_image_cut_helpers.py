"""Phần hình học cắt ảnh phải test được khi máy dev không cài rembg."""
from PIL import Image

from mcp_servers.image_cut_helpers import (
    apply_alpha_to_original,
    calculate_inference_size,
    read_nonnegative_env,
)


def test_anh_nho_hon_nguong_khong_bi_dung_vao():
    assert calculate_inference_size((1600, 1200), 2000) is None
    assert calculate_inference_size((2000, 1200), 2000) is None
    assert calculate_inference_size((4000, 3000), 0) is None


def test_anh_lon_giu_ti_le_va_can_dai_dung_bang_nguong():
    assert calculate_inference_size((4000, 3000), 2000) == (2000, 1500)
    assert calculate_inference_size((3000, 4000), 2000) == (1500, 2000)


def test_alpha_phong_len_dung_kich_thuoc_anh_goc():
    original = Image.new("RGB", (8, 4), (120, 80, 40))
    alpha_small = Image.new("L", (2, 1))
    alpha_small.putdata([0, 255])

    result = apply_alpha_to_original(original, alpha_small)

    assert result.mode == "RGBA"
    assert result.size == original.size
    assert result.getchannel("A").size == original.size
    assert result.getpixel((0, 0))[:3] == (120, 80, 40)
    assert result.getpixel((7, 3))[:3] == (120, 80, 40)


def test_env_sai_dinh_dang_quay_ve_mac_dinh():
    assert read_nonnegative_env("NGUONG", 2000, {"NGUONG": "khong-phai-so"}) == 2000
    assert read_nonnegative_env("NGUONG", 600, {"NGUONG": ""}) == 600


def test_env_bang_khong_hoac_am_deu_tat_tinh_nang():
    assert read_nonnegative_env("NGUONG", 2000, {"NGUONG": "0"}) == 0
    assert read_nonnegative_env("NGUONG", 2000, {"NGUONG": "-15"}) == 0
