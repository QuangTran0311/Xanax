"""Ghép ảnh sản phẩm đã tách nền lên một tấm nền.

Vì sao phải ghép tay thay vì bảo model vẽ luôn cả sản phẩm: hai bộ sinh ảnh đang
dùng (`/images/generations` và Codex imagegen) đều là text-to-image thuần, không
nhận ảnh đầu vào. Bảo model "vẽ đúng con đà điểu này" là bất khả — nó sẽ vẽ ra
một con khác. Mà ảnh đăng bán thì bắt buộc phải là hàng thật.

Nên chia đôi việc: model lo phần NỀN (nó vẽ tự do được), còn sản phẩm là ảnh chụp
thật đã tách nền, dán lên. Đổi lại phải tự lo bóng đổ, nếu không món hàng trông
như dán giấy lên tường.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageChops, ImageFilter, ImageMath, ImageStat

if TYPE_CHECKING:
    from core.poster_templates import NormalizedRegion

logger = logging.getLogger("xanax.image_compose")

# Chiều cao sản phẩm so với chiều cao nền. 0.68 để còn chỗ cho tiêu đề phía trên
# và tên trang phía dưới — hai thứ mọi ảnh của dự án đều phải có.
_DEFAULT_SCALE = 0.68
_DEFAULT_Y_OFFSET = 0.04
_MAX_WIDTH_RATIO = 0.82


def default_placement() -> tuple[float, float]:
    """(cao, xuống) mặc định. Để nơi khác hỏi thay vì chép lại hai con số này."""
    return _DEFAULT_SCALE, _DEFAULT_Y_OFFSET

# Dưới ngưỡng này coi như trong suốt hẳn. Trùng ngưỡng mà mcp_servers/image_cut.py
# dùng để tính khung cắt, nên hai bên hiểu "đâu là sản phẩm" giống nhau.
_ALPHA_FLOOR = 12

# Alpha tối thiểu dùng làm mẫu số khi khử nhiễm màu viền. Pixel alpha thật sự
# thấp thì màu quan sát gần như toàn là nền cũ, chia ngược sẽ khuếch đại nhiễu —
# nên kẹp mẫu số lại thay vì chia cho đúng alpha.
_UNMULT_FLOOR = 64

# Vành bán trong suốt dùng để đo xem ảnh vào đã được khử nhiễm sẵn hay chưa.
_EDGE_BAND = (12, 200)
# Vành tối hơn ruột dưới tỷ lệ này thì coi là còn dính màu nền cũ. 0.85 chừa chỗ
# cho việc vành vốn dĩ hơi tối tự nhiên do khuất sáng, không phải do nhiễm nền.
_CLEAN_EDGE_RATIO = 0.85


def _erode_one_pixel(alpha: Image.Image) -> Image.Image:
    """Co mặt nạ vào trong 1 pixel, giữ nguyên phần alpha mượt bên trong.

    MinFilter(3) co vào, GaussianBlur nhẹ cho biên khỏi răng cưa, rồi `darker`
    để chỗ nào vốn đã trong hơn thì giữ nguyên.
    """
    mask = alpha.point(lambda v: 255 if v >= _ALPHA_FLOOR else 0)
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    return ImageChops.darker(alpha, mask)


def _edge_is_contaminated(product: Image.Image, alpha: Image.Image) -> bool:
    """Vành bán trong suốt có còn tối bất thường so với ruột sản phẩm không.

    Từ khi `cut_product` bật alpha_matting mặc định, ảnh vào thường ĐÃ được khử
    nhiễm đúng cách rồi: matting của rembg gọi `estimate_foreground_ml`, trả về
    màu sản phẩm đã gỡ khỏi màu nền. Chia ngược alpha thêm lần nữa lên tấm đó là
    khử hai lần — vành biên bị đẩy sáng quá, len trắng ngả bạc.

    Mà hàm này không có cách nào biết ảnh vào đến từ đâu: nó chỉ nhận một file
    PNG. Nên thay vì thêm tham số rồi trông chờ nơi gọi truyền đúng, cứ đo: nếu
    vành không tối hơn ruột thì không có gì để khử.
    """
    gray = product.convert("RGB").convert("L")
    band = alpha.point(lambda v: 255 if _EDGE_BAND[0] <= v < _EDGE_BAND[1] else 0)
    core = alpha.point(lambda v: 255 if v >= 250 else 0)
    if not band.getbbox() or not core.getbbox():
        return False   # không có vành, hoặc không có ruột để so — bỏ qua
    band_mean = ImageStat.Stat(gray, band).mean[0]
    core_mean = ImageStat.Stat(gray, core).mean[0]
    logger.debug("Độ sáng vành %.1f / ruột %.1f", band_mean, core_mean)
    return band_mean < core_mean * _CLEAN_EDGE_RATIO


def decontaminate_edge(product: Image.Image) -> Image.Image:
    """Khử màu nền cũ còn dính ở vành bán trong suốt của ảnh đã tách nền.

    rembg giữ nguyên màu gốc của pixel ở biên, mà pixel biên trong ảnh chụp vốn
    đã là hỗn hợp giữa sản phẩm và nền phía sau. Đo trên ảnh con đà điểu chụp
    trên ba lô tối màu: 46.779 pixel biên, độ sáng trung bình 41.8 trong khi ruột
    sản phẩm là 156.7 — càng trong suốt càng tối, đúng dạng

        quan sát = màu_thật × alpha + màu_nền_cũ × (1 − alpha)

    Dán tấm đó lên nền kem thì cái vành tối hiện ra thành đường viền quanh sản
    phẩm. Ở đây coi nền cũ là đen rồi giải ngược ra màu thật (chia cho alpha),
    kèm bào mòn 1 pixel ngoài cùng — hàng ngoài cùng nhiễm nặng nhất và chia
    ngược không cứu nổi.

    Phép chia ngược chỉ chạy khi đo thấy vành thật sự còn nhiễm (xem
    `_edge_is_contaminated`). Bào mòn 1 pixel thì luôn chạy: rẻ, và hàng ngoài
    cùng thì mask nào cũng đáng ngờ.
    """
    r, g, b, alpha = product.split()

    if not _edge_is_contaminated(product, alpha):
        logger.info("Vành biên đã sạch sẵn — bỏ qua bước chia ngược alpha")
        cleaned = product.copy()
        cleaned.putalpha(_erode_one_pixel(alpha))
        return cleaned

    # Pillow ≥ 10.3 bỏ ImageMath.eval, thay bằng lambda_eval. Giữ cả hai nhánh để
    # không khoá dự án vào đúng một phiên bản Pillow.
    _eval = getattr(ImageMath, "lambda_eval", None)

    def _unmultiply(channel: Image.Image) -> Image.Image:
        args = {"c": channel, "a": alpha, "floor": _UNMULT_FLOOR}
        # `min`/`max` của ImageMath đòi toán hạng ĐẦU là ảnh, không phải số.
        if _eval is not None:
            return _eval(
                lambda kw: kw["convert"](
                    kw["min"](kw["c"] * 255 / kw["max"](kw["a"], kw["floor"]), 255), "L"),
                **args)
        return ImageMath.eval(  # Pillow cũ
            "convert(min(c * 255 / max(a, floor), 255), 'L')", **args)

    cleaned = Image.merge("RGBA", (_unmultiply(r), _unmultiply(g), _unmultiply(b), alpha))
    cleaned.putalpha(_erode_one_pixel(alpha))
    return cleaned


def compose_on_background(
    product_path: str | Path, background_path: str | Path, output_path: str | Path,
    *, scale: float = _DEFAULT_SCALE, y_offset: float = _DEFAULT_Y_OFFSET,
    shadow: bool = True, product_region: "NormalizedRegion | None" = None,
) -> Path:
    """Dán sản phẩm (PNG có alpha) vào giữa tấm nền, kèm bóng đổ mềm.

    `scale`    — chiều cao sản phẩm / chiều cao nền.
    `y_offset` — đẩy xuống dưới tâm bao nhiêu phần chiều cao nền. Đặt sản phẩm
                 đúng tâm hình học trông bị "trôi lên", vì mắt người coi khoảng
                 trống phía trên là một phần của bố cục.
    `product_region` — nếu có thì thắng scale/y_offset: đặt ảnh vừa khít cả chiều
                       rộng lẫn cao của ô, giữ tỷ lệ, canh ngang giữa và canh đáy.
                       Canh đáy khiến món hàng có cảm giác đứng trên mặt phẳng.
    """
    product = Image.open(product_path).convert("RGBA")
    background = Image.open(background_path).convert("RGBA")

    # Xoá hẳn những pixel gần trong suốt. rembg để lại cả vạn pixel alpha 1–11 —
    # tàn dư của nền ảnh chụp gốc. Trên nền trắng của trình xem ảnh thì không
    # thấy gì, nhưng dán lên nền màu là hiện ra một mảng chữ nhật sáng hơn quanh
    # sản phẩm, đúng bằng khung ảnh gốc. Đo trên ảnh thật: 20.895 pixel như vậy.
    alpha = product.getchannel("A").point(lambda v: v if v >= _ALPHA_FLOOR else 0)
    product.putalpha(alpha)

    # Rồi khử màu nền cũ dính ở vành bán trong suốt — xem decontaminate_edge.
    product = decontaminate_edge(product)
    alpha = product.getchannel("A")

    # Cắt sát theo alpha trước khi tính tỷ lệ: ảnh vào có thể còn viền trong suốt
    # thừa, không cắt thì "cao 68% nền" tính cả phần rỗng và sản phẩm hoá ra bé tí.
    bbox = alpha.point(lambda v: 255 if v >= _ALPHA_FLOOR else 0).getbbox()
    if bbox:
        product = product.crop(bbox)

    bg_w, bg_h = background.size
    if product_region is not None:
        left = round(product_region.left * bg_w)
        top = round(product_region.top * bg_h)
        right = round(product_region.right * bg_w)
        bottom = round(product_region.bottom * bg_h)
        region_w = max(1, right - left)
        region_h = max(1, bottom - top)
        fit = min(region_w / product.width, region_h / product.height)
        target_w = max(1, round(product.width * fit))
        target_h = max(1, round(product.height * fit))
        x = left + (region_w - target_w) // 2
        y = bottom - target_h
    else:
        target_h = max(1, int(bg_h * scale))
        target_w = max(1, int(product.width * target_h / product.height))
        if target_w > bg_w * _MAX_WIDTH_RATIO:
            target_w = int(bg_w * _MAX_WIDTH_RATIO)
            target_h = max(1, int(product.height * target_w / product.width))
        x = (bg_w - target_w) // 2
        y = int((bg_h - target_h) / 2 + bg_h * y_offset)
    product = product.resize((target_w, target_h), Image.LANCZOS)

    canvas = background.copy()
    if shadow:
        # Bóng = chính hình bóng của sản phẩm, làm mờ rồi hạ độ đậm. Dùng alpha của
        # sản phẩm nên bóng luôn khớp hình dạng thật, không cần biết nó là cái gì.
        #
        # Phải dán hình bóng lên tấm to bằng CẢ NỀN rồi mới làm mờ. Làm mờ trên
        # tấm chỉ to bằng sản phẩm thì vầng mờ lan tới mép tấm là bị xén cụt, để
        # lại một khung chữ nhật tối sắc cạnh đúng bằng khung sản phẩm — nhìn như
        # ai dán miếng ảnh lên nền. Ghép xong mới thấy, nên đã lọt qua một thời
        # gian dài.
        blur = max(2, int(target_h * 0.035))
        shade = Image.new("L", background.size, 0)
        shade.paste(product.getchannel("A").point(lambda v: int(v * 0.45)),
                    (x, y + int(target_h * 0.03)))
        silhouette = Image.new("RGBA", background.size, (0, 0, 0, 0))
        silhouette.putalpha(shade.filter(ImageFilter.GaussianBlur(blur)))
        canvas.alpha_composite(silhouette)

    canvas.alpha_composite(product, (x, y))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG", optimize=True)
    logger.info("Ghép sản phẩm %s lên nền %s → %s", product_path, background_path, out)
    return out
