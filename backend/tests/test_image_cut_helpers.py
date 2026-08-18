"""Phần hình học cắt ảnh phải test được khi máy dev không cài rembg."""
from PIL import Image

from mcp_servers.image_cut_helpers import (
    GIB,
    apply_alpha_to_original,
    calculate_available_memory,
    calculate_inference_size,
    memory_check_error,
    model_memory_requirement,
    read_nonnegative_env,
)


def _meminfo(gib: float) -> str:
    return f"MemTotal: 99999999 kB\nMemAvailable: {round(gib * GIB / 1024)} kB\n"


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


def test_birefnet_bi_chan_khi_ram_kha_dung_thap_hon_sau_gib():
    error = memory_check_error(
        "birefnet-general-lite", _meminfo(5), None, None, {},
    )

    assert error is not None
    assert "6 GiB" in error
    assert "5 GiB" in error
    assert "MemAvailable" in error
    assert "model='u2netp'" in error
    assert "518 MiB" in error
    assert "bóng đổ" in error


def test_birefnet_duoc_chay_khi_ram_kha_dung_du_sau_gib():
    assert memory_check_error(
        "birefnet-general-lite", _meminfo(6), None, None, {},
    ) is None
    assert model_memory_requirement("birefnet-massive")[0] == 6 * GIB


def test_u2netp_khong_bi_chan_o_muc_ram_ma_birefnet_bi_chan():
    meminfo = _meminfo(2)

    assert memory_check_error(
        "birefnet-general-lite", meminfo, None, None, {},
    ) is not None
    assert memory_check_error("u2netp", meminfo, None, None, {}) is None


def test_u2netp_bi_chan_khi_ram_kha_dung_duoi_mot_gib():
    error = memory_check_error("u2netp", _meminfo(0.5), None, None, {})

    assert error is not None
    assert "1 GiB" in error
    assert "512 MiB" in error


def test_nguon_nao_chat_hon_thi_nguon_do_thang():
    cgroup_chat_hon = calculate_available_memory(
        _meminfo(8), str(10 * GIB), str(5 * GIB),
    )
    memavailable_chat_hon = calculate_available_memory(
        _meminfo(4), str(10 * GIB), str(5 * GIB),
    )

    assert cgroup_chat_hon.bytes == 5 * GIB
    assert "cgroup" in cgroup_chat_hon.bottleneck
    assert "cgroup" in memory_check_error(
        "birefnet-general-lite", _meminfo(8), str(10 * GIB), str(5 * GIB), {},
    )
    assert memavailable_chat_hon.bytes == 4 * GIB
    assert "MemAvailable" in memavailable_chat_hon.bottleneck


def test_memory_max_la_max_thi_cgroup_duoc_coi_la_vo_han():
    available = calculate_available_memory(_meminfo(7), "max\n", str(99 * GIB))

    assert available.bytes == 7 * GIB
    assert "MemAvailable" in available.bottleneck
    assert memory_check_error(
        "birefnet-general-lite", _meminfo(7), "max", str(99 * GIB), {},
    ) is None


def test_file_ram_thieu_hoac_khong_doc_duoc_thi_khong_chan():
    assert memory_check_error(
        "birefnet-general-lite", None, None, None, {},
    ) is None
    assert memory_check_error(
        "birefnet-general-lite", "du lieu hong", "khong-phai-so", "?", {},
    ) is None


def test_model_la_khong_bi_chan_vi_chua_co_so_do():
    required, must_enforce = model_memory_requirement("model-chua-tung-do")

    assert required == 1 * GIB
    assert must_enforce is False
    assert memory_check_error(
        "model-chua-tung-do", _meminfo(0.05), "100", "99", {},
    ) is None


def test_env_tat_kiem_tra_thi_bo_qua_moi_nguon_ram():
    assert memory_check_error(
        "birefnet-general-lite",
        _meminfo(0),
        str(5 * GIB),
        str(5 * GIB),
        {"XANAX_IMAGE_CUT_SKIP_MEMORY_CHECK": "1"},
    ) is None
