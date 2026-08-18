"""Đo bố cục và vẽ lớp chữ poster cho ảnh có sản phẩm thật (chế độ B).

Module này cố ý chỉ dùng Pillow và thư viện chuẩn. Nó không biết web, database hay
model sinh ảnh, nhờ vậy có thể test toàn bộ việc xuống dòng, chọn font và tính vị
trí sản phẩm ngay trên máy dev, không cần mạng.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageStat


SCALE_RANGE = (0.30, 0.90)
OFFSET_RANGE = (-0.15, 0.15)
CONTENT_WIDTH_RATIO = 0.82

# 4.5:1 là ngưỡng WCAG cho chữ thường. Poster không phải trang web, nhưng dùng
# cùng ngưỡng đã được kiểm chứng sẽ chắc hơn một con số chọn theo cảm giác.
MIN_TEXT_CONTRAST = 4.5
MIN_OUTLINE_CONTRAST = 3.0
_VIETNAMESE_PROBE = "ệ ữ ạ ỗ ằ"
_TOFU_PROBES = ("\ufffd", "\u25a1", "\u0378")


class VietnameseFontError(RuntimeError):
    """Không tìm được font có đủ glyph tiếng Việt."""


@dataclass(frozen=True)
class FontFamily:
    regular: str
    bold: str
    name: str


@dataclass(frozen=True)
class PosterPalette:
    """Bảng màu trung tính; caller có thể truyền mapping để gắn màu thương hiệu."""

    light_text: tuple[int, int, int] = (255, 253, 248)
    dark_text: tuple[int, int, int] = (32, 27, 24)
    accent: tuple[int, int, int] = (190, 82, 48)
    panel_light: tuple[int, int, int] = (255, 252, 245)
    panel_dark: tuple[int, int, int] = (24, 20, 18)


@dataclass(frozen=True)
class TextElement:
    kind: str
    lines: tuple[str, ...]
    font_size: int
    bold: bool
    height: int
    box_width: int


@dataclass(frozen=True)
class TextContrastTreatment:
    """Cách giữ một dòng chữ đọc được trên đúng phần nền mà dòng đó đi qua."""

    text_color: tuple[int, int, int]
    mode: str
    local_contrast: float
    outline_color: tuple[int, int, int] | None = None
    panel_fill: tuple[int, int, int] | None = None
    panel_alpha: int = 0


@dataclass(frozen=True)
class PosterLayout:
    size: tuple[int, int]
    content_width: int
    top_box: tuple[int, int, int, int]
    bottom_box: tuple[int, int, int, int]
    top_elements: tuple[TextElement, ...]
    bottom_elements: tuple[TextElement, ...]
    product_scale: float
    product_y_offset: float
    text_scale: float
    features_used: int
    font_family: FontFamily


# Thứ tự này vừa ưu tiên font thiết kế đẹp, vừa phủ đường dẫn thường gặp trên
# Windows và Ubuntu. Mỗi family vẫn phải qua kiểm glyph bên dưới; tên đẹp nhưng
# thiếu dấu tiếng Việt sẽ bị bỏ qua, không được phép âm thầm vẽ ô vuông.
_FONT_CANDIDATES: tuple[tuple[str, str, str], ...] = (
    ("Be Vietnam Pro", "C:/Windows/Fonts/BeVietnamPro-Regular.ttf", "C:/Windows/Fonts/BeVietnamPro-Bold.ttf"),
    ("Be Vietnam Pro", "/usr/share/fonts/truetype/be-vietnam-pro/BeVietnamPro-Regular.ttf", "/usr/share/fonts/truetype/be-vietnam-pro/BeVietnamPro-Bold.ttf"),
    ("Inter", "C:/Windows/Fonts/Inter-Regular.ttf", "C:/Windows/Fonts/Inter-Bold.ttf"),
    ("Inter", "/usr/share/fonts/truetype/inter/Inter-Regular.ttf", "/usr/share/fonts/truetype/inter/Inter-Bold.ttf"),
    ("Inter", "/usr/share/fonts/truetype/inter-vf/Inter.var.ttf", "/usr/share/fonts/truetype/inter-vf/Inter.var.ttf"),
    ("Inter", "/usr/share/fonts/opentype/inter/Inter-Regular.otf", "/usr/share/fonts/opentype/inter/Inter-Bold.otf"),
    ("Montserrat", "C:/Windows/Fonts/Montserrat-Regular.ttf", "C:/Windows/Fonts/Montserrat-Bold.ttf"),
    ("Montserrat", "/usr/share/fonts/truetype/montserrat/Montserrat-Regular.ttf", "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf"),
    ("Noto Sans", "C:/Windows/Fonts/NotoSans-Regular.ttf", "C:/Windows/Fonts/NotoSans-Bold.ttf"),
    ("Noto Sans", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
    ("Segoe UI", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("Arial", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("DejaVu Sans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("Liberation Sans", "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
    ("Liberation Sans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
)


def _glyph_signature(font: ImageFont.FreeTypeFont, char: str) -> tuple:
    """Lấy chữ ký bitmap, gồm cả bbox để phân biệt các glyph có cùng số byte."""

    mask = font.getmask(char, mode="L")
    return font.getbbox(char), mask.size, bytes(mask)


def font_supports_vietnamese(path: str | Path) -> bool:
    """Kiểm font thật sự vẽ được các dấu khó, thay vì chỉ kiểm file tồn tại.

    FreeType thay glyph bị thiếu bằng `.notdef` (tofu). So bitmap từng chữ tiếng
    Việt với U+FFFD, ô vuông và một code point chưa gán sẽ bắt được cả ba cách
    font thường biểu diễn glyph thiếu mà không cần thêm dependency đọc bảng cmap.
    """

    try:
        font = ImageFont.truetype(str(path), 48)
        tofu = {_glyph_signature(font, char) for char in _TOFU_PROBES}
        signatures = []
        for char in _VIETNAMESE_PROBE.replace(" ", ""):
            signature = _glyph_signature(font, char)
            if signature in tofu:
                return False
            signatures.append(signature)
        # Một font trả cùng `.notdef` nhưng không trùng các probe ở trên vẫn sẽ
        # làm mọi chữ khó giống hệt nhau; đây là lớp bảo vệ thứ hai.
        return len(set(signatures)) >= 4
    except (OSError, ValueError, TypeError):
        return False


def resolve_font_family(
    candidates: Sequence[tuple[str, str, str]] | None = None,
) -> FontFamily:
    """Chọn family đầu tiên có đủ dấu ở cả regular và bold.

    Nếu thiếu riêng bold nhưng regular tốt, dùng regular cho cả hai: chữ vẫn đúng
    dấu và hierarchy còn được giữ bằng cỡ/chip. Thiếu toàn bộ thì báo lỗi rõ thay
    vì rơi về ``ImageFont.load_default()`` vốn dễ sinh poster đầy tofu.
    """

    for name, regular, bold in candidates or _FONT_CANDIDATES:
        if not Path(regular).is_file() or not font_supports_vietnamese(regular):
            continue
        usable_bold = bold if Path(bold).is_file() and font_supports_vietnamese(bold) else regular
        return FontFamily(regular=regular, bold=usable_bold, name=name)
    raise VietnameseFontError(
        "Không tìm thấy font hỗ trợ đầy đủ tiếng Việt. Hãy cài Be Vietnam Pro, "
        "Inter, Montserrat hoặc gói fonts-dejavu-core/fonts-liberation trên Ubuntu."
    )


def normalize_poster(content: Mapping | None) -> dict:
    """Giữ đúng contract title/tagline/features/price/cta/handle và bỏ field rỗng."""

    if not isinstance(content, Mapping):
        return {}
    clean: dict[str, object] = {}
    for key in ("title", "tagline", "price", "cta", "handle"):
        value = content.get(key)
        if value is not None and str(value).strip():
            clean[key] = str(value).strip()

    raw_features = content.get("features")
    if isinstance(raw_features, str):
        raw_features = raw_features.splitlines()
    if isinstance(raw_features, Sequence) and not isinstance(raw_features, (bytes, bytearray)):
        features = [
            str(value).strip() for value in raw_features
            if value is not None and str(value).strip()
        ]
        if features:
            clean["features"] = features[:3]
    return clean


def _font(family: FontFamily, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(family.bold if bold else family.regular, size)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> float:
    return draw.textlength(text, font=font)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Xuống dòng theo pixel; từ quá dài cũng được bẻ theo ký tự, không tràn khung."""

    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if _text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        if _text_width(draw, word, font) <= max_width:
            current = word
            continue

        part = ""
        for char in word:
            if part and _text_width(draw, part + char, font) > max_width:
                lines.append(part)
                part = char
            else:
                part += char
        current = part
    if current:
        lines.append(current)
    return lines


def _ellipsize(line: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    suffix = "…"
    while line and _text_width(draw, line + suffix, font) > max_width:
        line = line[:-1].rstrip()
    return line + suffix if line else suffix


def _fit_element(
    kind: str,
    text: str,
    family: FontFamily,
    preferred_size: int,
    min_size: int,
    max_width: int,
    max_lines: int,
    *,
    bold: bool,
    vertical_padding: int = 0,
    horizontal_reserve: int = 0,
    hug_width: bool = True,
) -> TextElement:
    """Giảm font trước khi cắt dòng; dấu ba chấm chỉ là hàng rào cho input dị thường."""

    text_width = max(1, max_width - horizontal_reserve)
    size = max(min_size, preferred_size)
    while size > min_size:
        font = _font(family, size, bold)
        lines = wrap_text(text, font, text_width)
        if len(lines) <= max_lines:
            break
        size = max(min_size, size - 2)
    font = _font(family, size, bold)
    lines = wrap_text(text, font, text_width) or [""]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _ellipsize(lines[-1], font, text_width)
    line_height = max(1, int(size * 1.24))
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    measured_width = math.ceil(max(_text_width(draw, line, font) for line in lines))
    return TextElement(
        kind=kind,
        lines=tuple(lines),
        font_size=size,
        bold=bold,
        height=line_height * len(lines) + vertical_padding * 2,
        box_width=max_width if not hug_width else min(max_width, measured_width + horizontal_reserve),
    )


def _block_height(elements: Sequence[TextElement], gap: int, panel_padding: int) -> int:
    if not elements:
        return 0
    return sum(item.height for item in elements) + gap * (len(elements) - 1) + panel_padding * 2


def _make_elements(
    size: tuple[int, int],
    content: Mapping,
    family: FontFamily,
    text_scale: float,
    feature_count: int,
) -> tuple[tuple[TextElement, ...], tuple[TextElement, ...], int, int, int, int]:
    width, height = size
    short = min(width, height)
    content_width = max(1, int(width * CONTENT_WIDTH_RATIO))
    gap = max(6, int(short * 0.012))
    panel_padding = max(10, int(short * 0.020))
    chip_padding = max(6, int(short * 0.010))

    def scaled(ratio: float, floor: int) -> int:
        return max(floor, int(short * ratio * text_scale))

    minimum = max(12, int(short * 0.018))
    top: list[TextElement] = []
    bottom: list[TextElement] = []
    if content.get("title"):
        top.append(_fit_element("title", str(content["title"]), family,
                                scaled(0.066, 24), minimum, content_width, 2, bold=True))
    if content.get("tagline"):
        top.append(_fit_element("tagline", str(content["tagline"]), family,
                                scaled(0.034, 18), minimum, content_width, 2, bold=False))

    features = list(content.get("features") or [])[:feature_count]
    for feature in features:
        # Chip ôm nội dung: 4 padding bên trái dành cho chấm + vị trí bắt đầu chữ,
        # 2 padding bên phải để pill cân mắt. Chỉ khi tổng này chạm content width
        # thì chữ mới xuống dòng/thu nhỏ; không kéo pill ngắn thành một thanh dài.
        bottom.append(_fit_element("feature", str(feature), family,
                                   scaled(0.027, 16), minimum, content_width,
                                   2, bold=False, vertical_padding=chip_padding,
                                   horizontal_reserve=chip_padding * 6))
    if content.get("price"):
        bottom.append(_fit_element("price", str(content["price"]), family,
                                   scaled(0.050, 22), minimum, content_width, 1,
                                   bold=True, vertical_padding=chip_padding,
                                   horizontal_reserve=chip_padding * 5))
    if content.get("cta"):
        bottom.append(_fit_element("cta", str(content["cta"]), family,
                                   scaled(0.031, 18), minimum, content_width,
                                   2, bold=True, vertical_padding=chip_padding,
                                   horizontal_reserve=chip_padding * 4, hug_width=False))
    if content.get("handle"):
        bottom.append(_fit_element("handle", str(content["handle"]), family,
                                   scaled(0.024, 15), minimum, content_width, 2, bold=False))
    return tuple(top), tuple(bottom), gap, panel_padding, chip_padding, content_width


def _clamp(value: float, bounds: tuple[float, float]) -> float:
    return min(max(value, bounds[0]), bounds[1])


def build_poster_layout(
    size: tuple[int, int],
    content: Mapping,
    *,
    explicit_placement: tuple[float, float] | None = None,
    font_family: FontFamily | None = None,
) -> PosterLayout:
    """Đo chữ trước và biến khoảng còn lại thành ``cao``/``xuống`` của sản phẩm.

    Khi chữ quá nhiều, thứ tự đánh đổi là giảm cỡ chữ rồi bỏ feature cuối. Title,
    giá và CTA được giữ vì chúng định danh món hàng/chốt bán; sản phẩm luôn được
    dành tối thiểu 30% chiều cao vì người xem mua món hàng chứ không mua chữ.
    ``explicit_placement`` thắng hoàn toàn phép tính tự động, chỉ bị kẹp an toàn.
    """

    clean = normalize_poster(content)
    if not clean:
        raise ValueError("POSTER không có trường nội dung nào để vẽ")
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError("Kích thước poster phải lớn hơn 0")
    family = font_family or resolve_font_family()
    feature_total = len(clean.get("features") or [])
    outer_y = max(8, int(height * 0.032))
    chosen = None
    # Chỉ cắt feature sau khi đã thử đủ các mức co chữ. Điều này giữ thông tin
    # bán hàng nếu chỉ cần giảm nhẹ typography, nhưng không hy sinh kích thước món.
    for count in range(feature_total, -1, -1):
        for text_scale in (1.0, 0.90, 0.80, 0.70, 0.60, 0.50):
            top, bottom, gap, panel_padding, _, content_width = _make_elements(
                size, clean, family, text_scale, count)
            top_h = _block_height(top, gap, panel_padding)
            bottom_h = _block_height(bottom, gap, panel_padding)
            # Khoảng của sản phẩm bắt đầu sau dòng chữ thật, không phải sau phần
            # padding trong suốt của panel. Bóng 3% trên / 5% dưới là bleed do bộ
            # ghép vẽ quanh alpha sản phẩm; trừ chúng thêm theo chiều cao canvas sẽ
            # biến đúng hai biên ấy thành hai dải trắng cố định và làm món bị teo.
            # Vì vậy giao trọn khoảng nhìn thấy này cho `cao`, còn panel padding
            # chỉ làm nhiệm vụ đệm chữ và không được tính như nội dung chiếm chỗ.
            product_top = outer_y + top_h - (panel_padding if top else 0)
            product_bottom = (
                height - outer_y - bottom_h + (panel_padding if bottom else 0)
            )
            raw_scale = (product_bottom - product_top) / height
            chosen = (top, bottom, gap, panel_padding, top_h, bottom_h,
                      product_top, product_bottom, raw_scale, text_scale, count,
                      content_width)
            if raw_scale >= SCALE_RANGE[0]:
                break
        if chosen and chosen[8] >= SCALE_RANGE[0]:
            break

    assert chosen is not None
    (top, bottom, _gap, _panel_padding, top_h, bottom_h,
     product_top, product_bottom, raw_scale, text_scale, count, content_width) = chosen
    x0 = (width - content_width) // 2
    x1 = x0 + content_width
    top_box = (x0, outer_y, x1, outer_y + top_h) if top else (0, 0, 0, 0)
    bottom_box = (
        (x0, height - outer_y - bottom_h, x1, height - outer_y)
        if bottom else (0, 0, 0, 0)
    )

    if explicit_placement is not None:
        product_scale = _clamp(float(explicit_placement[0]), SCALE_RANGE)
        y_offset = _clamp(float(explicit_placement[1]), OFFSET_RANGE)
    else:
        product_scale = _clamp(raw_scale, SCALE_RANGE)
        center_y = (product_top + product_bottom) / 2
        y_offset = _clamp(center_y / height - 0.5, OFFSET_RANGE)

    return PosterLayout(
        size=size,
        content_width=content_width,
        top_box=top_box,
        bottom_box=bottom_box,
        top_elements=top,
        bottom_elements=bottom,
        product_scale=product_scale,
        product_y_offset=y_offset,
        text_scale=text_scale,
        features_used=count,
        font_family=family,
    )


def _rgb(value) -> tuple[int, int, int]:
    if isinstance(value, str):
        return ImageColor.getrgb(value)
    if isinstance(value, Sequence) and len(value) >= 3:
        return tuple(int(_clamp(float(channel), (0, 255))) for channel in value[:3])
    raise ValueError(f"Màu không hợp lệ: {value!r}")


def make_palette(values: Mapping | PosterPalette | None = None) -> PosterPalette:
    if isinstance(values, PosterPalette):
        return values
    defaults = PosterPalette()
    if not values:
        return defaults
    return PosterPalette(**{
        field: _rgb(values.get(field, getattr(defaults, field)))
        for field in ("light_text", "dark_text", "accent", "panel_light", "panel_dark")
    })


def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    channels = []
    for value in rgb:
        value /= 255.0
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(a: float, b: float) -> float:
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def _luminance_bounds(
    image: Image.Image,
    box: tuple[int, int, int, int],
) -> tuple[float, float] | None:
    """Trả percentile 5–95 của độ sáng trong một bbox dòng chữ.

    Bỏ 5% hai đầu để một pixel nhiễu/viền anti-alias không ép cả dòng phải có
    panel, nhưng vẫn bắt được một mảng nền sáng/tối đủ lớn để thật sự nuốt chữ.
    """

    region = image.convert("RGB").crop(box)
    if region.width <= 0 or region.height <= 0:
        return None
    pixels = region.load()
    luminances = sorted(
        _relative_luminance(pixels[x, y])
        for y in range(region.height)
        for x in range(region.width)
    )
    last = len(luminances) - 1
    return luminances[int(last * 0.05)], luminances[int(last * 0.95)]


def _worst_contrast(
    text_color: tuple[int, int, int],
    bounds: tuple[float, float] | None,
) -> float:
    if bounds is None:
        return float("inf")
    text_l = _relative_luminance(text_color)
    return min(_contrast(text_l, bounds[0]), _contrast(text_l, bounds[1]))


def _mean_color(
    image: Image.Image,
    box: tuple[int, int, int, int],
) -> tuple[int, int, int]:
    region = image.convert("RGB").crop(box)
    if region.width <= 0 or region.height <= 0:
        return (128, 128, 128)
    return tuple(round(value) for value in ImageStat.Stat(region).mean[:3])


def _shift_tone(
    color: tuple[int, int, int],
    *,
    lighter: bool,
    strength: float,
) -> tuple[int, int, int]:
    target = 255 if lighter else 0
    return tuple(round(channel + (target - channel) * strength) for channel in color)


def choose_text_color(
    image: Image.Image,
    box: tuple[int, int, int, int],
    palette: Mapping | PosterPalette | None = None,
) -> tuple[int, int, int]:
    """Chọn chữ sáng/tối tốt hơn trên chính bbox của một dòng chữ."""

    colors = make_palette(palette)
    bounds = _luminance_bounds(image, box)
    if bounds is None:
        return colors.dark_text
    light_ratio = _worst_contrast(colors.light_text, bounds)
    dark_ratio = _worst_contrast(colors.dark_text, bounds)
    return colors.light_text if light_ratio >= dark_ratio else colors.dark_text


def _panel_style_from_background(
    image: Image.Image,
    box: tuple[int, int, int, int],
    text_color: tuple[int, int, int],
) -> tuple[tuple[int, int, int], int]:
    """Tạo màu panel từ màu nền tại chỗ, rồi nâng/hạ sáng vừa đủ tương phản."""

    region = image.convert("RGB").crop(box)
    mean = _mean_color(image, box)
    lighter = _relative_luminance(text_color) < 0.5
    if region.width <= 0 or region.height <= 0:
        return _shift_tone(mean, lighter=lighter, strength=0.7), 208

    # Tìm phương án ít tác động nhất trước. Fill luôn bắt đầu từ màu nền trung
    # bình nên nền kem vẫn ra kem, nền nâu vẫn ra nâu; chỉ lightness thay đổi.
    candidates = sorted(
        ((alpha * strength, alpha, strength)
         for alpha in (152, 176, 200, 224, 236)
         for strength in (0.30, 0.45, 0.60, 0.75, 0.90)),
        key=lambda item: item[0],
    )
    for _impact, alpha, strength in candidates:
        fill = _shift_tone(mean, lighter=lighter, strength=strength)
        preview = Image.blend(
            region,
            Image.new("RGB", region.size, fill),
            alpha / 255.0,
        )
        preview_box = (0, 0, preview.width, preview.height)
        if _worst_contrast(
            text_color, _luminance_bounds(preview, preview_box)
        ) >= MIN_TEXT_CONTRAST:
            return fill, alpha
    return _shift_tone(mean, lighter=lighter, strength=0.90), 236


def _choose_text_treatment(
    image: Image.Image,
    box: tuple[int, int, int, int],
    palette: PosterPalette,
) -> TextContrastTreatment:
    """Leo thang tương phản theo từng dòng, từ nhẹ đến nặng.

    Đầu tiên đổi giữa chữ sáng/tối vì không che nền. Nếu chỉ thiếu nhẹ (ít nhất
    3:1), viền/bóng mảnh đã tách cạnh glyph mà vẫn giữ nguyên ảnh. Chỉ khi cả màu
    chữ tốt nhất còn dưới mức đó mới dùng panel: lúc ấy một outline mảnh không đủ
    giữ phần ruột chữ rõ trên nền biến thiên mạnh. Panel được tính từ màu nền tại
    đúng bbox dòng và cũng chỉ ôm dòng đó, không trải ngang cả khối nội dung.
    """

    bounds = _luminance_bounds(image, box)
    text_color = choose_text_color(image, box, palette)
    ratio = _worst_contrast(text_color, bounds)
    opposite = (
        palette.dark_text
        if text_color == palette.light_text
        else palette.light_text
    )
    if ratio >= MIN_TEXT_CONTRAST:
        return TextContrastTreatment(text_color, "plain", ratio)
    if ratio >= MIN_OUTLINE_CONTRAST:
        return TextContrastTreatment(text_color, "outline", ratio, outline_color=opposite)
    panel_fill, panel_alpha = _panel_style_from_background(image, box, text_color)
    return TextContrastTreatment(
        text_color, "panel", ratio, panel_fill=panel_fill, panel_alpha=panel_alpha)


def _draw_soft_panel(
    image: Image.Image,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int],
    alpha: int,
) -> Image.Image:
    """Panel bán trong suốt, bo/blur theo chiều cao dòng thay vì theo cả canvas."""

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    mask = Image.new("L", image.size, 0)
    md = ImageDraw.Draw(mask)
    radius = max(4, min((box[3] - box[1]) // 2, int(min(image.size) * 0.018)))
    md.rounded_rectangle(box, radius=radius, fill=alpha)
    mask = mask.filter(ImageFilter.GaussianBlur(max(1, radius // 5)))
    color = Image.new("RGBA", image.size, (*fill, 255))
    overlay = Image.composite(color, overlay, mask)
    return Image.alpha_composite(image, overlay)


def _expanded_line_box(
    box: tuple[int, int, int, int],
    image_size: tuple[int, int],
    font_size: int,
) -> tuple[int, int, int, int]:
    pad_x = max(6, int(font_size * 0.24))
    pad_y = max(3, int(font_size * 0.12))
    return (
        max(0, box[0] - pad_x), max(0, box[1] - pad_y),
        min(image_size[0], box[2] + pad_x), min(image_size[1], box[3] + pad_y),
    )


def _draw_adaptive_line(
    image: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: float,
    y: int,
    palette: PosterPalette,
) -> Image.Image:
    """Đo và vẽ một dòng; không để vùng trống của block ảnh hưởng quyết định."""

    probe = ImageDraw.Draw(image)
    measured = probe.textbbox((x, y), text, font=font)
    if measured[2] <= measured[0] or measured[3] <= measured[1]:
        return image
    treatment = _choose_text_treatment(image, measured, palette)
    if treatment.mode == "panel":
        panel_box = _expanded_line_box(measured, image.size, font.size)
        image = _draw_soft_panel(
            image, panel_box, treatment.panel_fill or _mean_color(image, measured),
            treatment.panel_alpha)

    if treatment.mode == "outline":
        stroke = max(1, int(min(image.size) * 0.0015))
        layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        layer_draw = ImageDraw.Draw(layer)
        outline = treatment.outline_color or palette.dark_text
        # Bóng lệch 1 stroke kế thừa kỹ thuật overlay cũ của repo; viền mảnh giữ
        # cạnh chữ rõ ở phía còn lại mà không biến glyph thành chữ đậm giả.
        layer_draw.text((x + stroke, y + stroke), text, font=font,
                        fill=(*outline, 105))
        layer_draw.text((x, y), text, font=font, fill=(*treatment.text_color, 255),
                        stroke_width=stroke, stroke_fill=(*outline, 205))
        return Image.alpha_composite(image, layer)

    draw = ImageDraw.Draw(image)
    draw.text((x, y), text, font=font, fill=(*treatment.text_color, 255))
    return image


def _draw_centered_adaptive_lines(
    image: Image.Image,
    lines: Sequence[str],
    font: ImageFont.FreeTypeFont,
    center_x: int,
    y: int,
    line_height: int,
    palette: PosterPalette,
) -> Image.Image:
    for line in lines:
        draw = ImageDraw.Draw(image)
        width = draw.textlength(line, font=font)
        image = _draw_adaptive_line(
            image, line, font, center_x - width / 2, y, palette)
        y += line_height
    return image


def _draw_block(
    image: Image.Image,
    box: tuple[int, int, int, int],
    elements: Sequence[TextElement],
    family: FontFamily,
    palette: PosterPalette,
) -> Image.Image:
    if not elements:
        return image
    short = min(image.size)
    gap = max(6, int(short * 0.012))
    panel_padding = max(10, int(short * 0.020))
    chip_padding = max(6, int(short * 0.010))
    center_x = (box[0] + box[2]) // 2
    y = box[1] + panel_padding
    accent_text = (
        palette.light_text
        if _contrast(_relative_luminance(palette.light_text), _relative_luminance(palette.accent))
        >= _contrast(_relative_luminance(palette.dark_text), _relative_luminance(palette.accent))
        else palette.dark_text
    )

    for element in elements:
        font = _font(family, element.font_size, element.bold)
        line_height = max(1, int(element.font_size * 1.24))
        if element.kind == "feature":
            chip = (center_x - element.box_width // 2, y,
                    center_x + (element.box_width + 1) // 2, y + element.height)
            chip_text_color = choose_text_color(image, chip, palette)
            # Chip là thành phần thiết kế luôn có, nhưng màu cũng phải ăn theo nền
            # tại chỗ thay vì rơi về panel_light/panel_dark cố định.
            chip_fill = _shift_tone(
                _mean_color(image, chip),
                lighter=chip_text_color != palette.light_text,
                strength=0.24,
            )
            # ImageDraw ghi alpha đè thẳng lên RGBA thay vì blend. Vẽ chip trên
            # layer riêng rồi composite để alpha 72 thật sự giữ lại nền bên dưới.
            chip_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            chip_draw = ImageDraw.Draw(chip_layer)
            chip_draw.rounded_rectangle(
                chip, radius=element.height // 2,
                fill=(*chip_fill, 72), outline=(*chip_text_color, 46), width=1,
            )
            image = Image.alpha_composite(image, chip_layer)
            draw = ImageDraw.Draw(image)
            dot_x = chip[0] + chip_padding * 2
            dot_y = (chip[1] + chip[3]) // 2
            dot_r = max(3, element.font_size // 7)
            draw.ellipse((dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r),
                         fill=(*palette.accent, 255))
            text_y = y + chip_padding
            for line in element.lines:
                image = _draw_adaptive_line(
                    image, line, font, chip[0] + chip_padding * 4, text_y, palette)
                draw = ImageDraw.Draw(image)
                text_y += line_height
        elif element.kind in ("price", "cta"):
            pill_width = element.box_width
            pill = (center_x - pill_width // 2, y, center_x + pill_width // 2,
                    y + element.height)
            draw.rounded_rectangle(pill, radius=element.height // 2,
                                   fill=(*palette.accent, 255))
            text_y = y + chip_padding
            for line in element.lines:
                width = draw.textlength(line, font=font)
                draw.text((center_x - width / 2, text_y), line, font=font,
                          fill=(*accent_text, 255))
                text_y += line_height
        else:
            image = _draw_centered_adaptive_lines(
                image, element.lines, font, center_x, y, line_height, palette)
            draw = ImageDraw.Draw(image)
        y += element.height + gap
    return image


def render_poster_layer(
    image: Image.Image,
    layout: PosterLayout,
    *,
    palette: Mapping | PosterPalette | None = None,
) -> Image.Image:
    """Vẽ poster lên ảnh đã ghép sản phẩm và trả ảnh RGB mới."""

    if image.size != layout.size:
        raise ValueError(f"Ảnh {image.size} không khớp layout {layout.size}")
    colors = make_palette(palette)
    result = image.convert("RGBA")
    result = _draw_block(result, layout.top_box, layout.top_elements,
                         layout.font_family, colors)
    result = _draw_block(result, layout.bottom_box, layout.bottom_elements,
                         layout.font_family, colors)
    return result.convert("RGB")
