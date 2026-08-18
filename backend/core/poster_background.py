"""Đo xem model có giữ vùng dán sản phẩm thành một phần tự nhiên của cảnh hay không."""
from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFilter, ImageStat

from core.poster_templates import NormalizedRegion


@dataclass(frozen=True)
class EmptyRegionMeasurement:
    empty: bool
    edge_density: float
    outside_edge_density: float
    color_stddev: float
    outside_color_stddev: float
    mean_color_distance: float
    boundary_edge_density: float
    boundary_violation: bool
    flat_panel_violation: bool
    content_violation: bool

    def log_summary(self) -> str:
        violations = ",".join(
            name for name, active in (
                ("khung", self.boundary_violation),
                ("panel", self.flat_panel_violation),
                ("vật_thể", self.content_violation),
            ) if active
        ) or "không"
        return (
            f"empty={self.empty}, edge_ruột={self.edge_density:.3f} "
            f"(ngoài_sát={self.outside_edge_density:.3f}), "
            f"edge_viền={self.boundary_edge_density:.3f}, "
            f"std={self.color_stddev:.1f} (ngoài_sát={self.outside_color_stddev:.1f}), "
            f"lệch_màu_cục_bộ={self.mean_color_distance:.1f}, vi_phạm={violations}"
        )


def _pixel_box(size: tuple[int, int], region: NormalizedRegion) -> tuple[int, int, int, int]:
    width, height = size
    return (
        max(0, min(width - 1, round(region.left * width))),
        max(0, min(height - 1, round(region.top * height))),
        max(1, min(width, round(region.right * width))),
        max(1, min(height, round(region.bottom * height))),
    )


def _clamp_box(
    size: tuple[int, int], box: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    width, height = size
    left, top, right, bottom = box
    left = max(0, min(width - 1, left))
    top = max(0, min(height - 1, top))
    right = max(left + 1, min(width, right))
    bottom = max(top + 1, min(height, bottom))
    return left, top, right, bottom


def _box_mask(
    size: tuple[int, int], box: tuple[int, int, int, int], value: int = 255,
) -> Image.Image:
    mask = Image.new("L", size, 0)
    left, top, right, bottom = _clamp_box(size, box)
    ImageDraw.Draw(mask).rectangle((left, top, right - 1, bottom - 1), fill=value)
    return mask


def _ring_mask(
    size: tuple[int, int], outer: tuple[int, int, int, int],
    inner: tuple[int, int, int, int],
) -> Image.Image:
    mask = _box_mask(size, outer)
    left, top, right, bottom = _clamp_box(size, inner)
    ImageDraw.Draw(mask).rectangle((left, top, right - 1, bottom - 1), fill=0)
    return mask


def _edge_density(edges: Image.Image, mask: Image.Image) -> float:
    count = ImageStat.Stat(mask).sum[0] / 255
    if count <= 0:
        return 0.0
    return (ImageStat.Stat(edges, mask).sum[0] / 255) / count


def _mean_distance(first: ImageStat.Stat, second: ImageStat.Stat) -> float:
    return sum(abs(a - b) for a, b in zip(first.mean, second.mean)) / 3


def _side_color_distances(
    rgb: Image.Image, box: tuple[int, int, int, int], band: int,
) -> tuple[float, ...]:
    """So từng dải ngay trong mép ô với dải ngay ngoài mép tương ứng."""
    left, top, right, bottom = box
    trim = band
    pairs = (
        ((left, top + trim, left + band, bottom - trim),
         (left - band, top + trim, left, bottom - trim)),
        ((right - band, top + trim, right, bottom - trim),
         (right, top + trim, right + band, bottom - trim)),
        ((left + trim, top, right - trim, top + band),
         (left + trim, top - band, right - trim, top)),
        ((left + trim, bottom - band, right - trim, bottom),
         (left + trim, bottom, right - trim, bottom + band)),
    )
    distances = []
    for inside_box, outside_box in pairs:
        inside = ImageStat.Stat(rgb.crop(_clamp_box(rgb.size, inside_box)))
        outside = ImageStat.Stat(rgb.crop(_clamp_box(rgb.size, outside_box)))
        distances.append(_mean_distance(inside, outside))
    return tuple(distances)


def measure_empty_product_region(
    image: Image.Image, region: NormalizedRegion,
) -> EmptyRegionMeasurement:
    """Phát hiện vật thể, khung chữ nhật và panel phủ đúng vùng sản phẩm.

    Dải dò viền rộng 2% cạnh ngắn của vùng (giới hạn 2–8 px), đủ ôm hai mép của
    nét viền 1–4 px nhưng chưa rộng đến mức hút nhiều chi tiết cảnh. Viền bị coi là
    khung khi mật độ biên đạt 5,5% và đồng thời cao hơn ít nhất 1,8 lần ruột lẫn
    vùng ngoài lân cận. Panel không viền bị bắt khi ít nhất hai trong bốn cặp dải
    màu ngay sát mép lệch trung bình từ 18/255; điều kiện hai cạnh giúp đường chân
    tường hoặc mép bàn tự nhiên chỉ cắt ngang một cạnh vẫn qua.

    Các mốc 5,5%, 1,8 lần và 18 được chốt bằng ảnh giả trong test: gradient có mặt
    bàn chạy xuyên ô phải đạt; panel kem có/không viền đứt nét phải trượt. Ngưỡng
    vật thể cũ (biên 6–9%, độ lệch chuẩn 28–38) được giữ để không làm mất hành vi
    bắt chi tiết nằm trong vùng.
    """
    rgb = image.convert("RGB")
    gray = rgb.convert("L")
    # FIND_EDGES tạo viền giả ở mép toàn ảnh; mọi mask dưới đây đều nằm xa mép đó.
    edges = gray.filter(ImageFilter.FIND_EDGES).point(
        lambda value: 255 if value >= 28 else 0)
    box = _pixel_box(rgb.size, region)
    left, top, right, bottom = box
    short_side = min(right - left, bottom - top)
    border_band = max(2, min(8, round(short_side * 0.02)))
    color_band = max(6, min(20, round(short_side * 0.04)))

    # Dải giữa ôm đúng đường viền; hai mask tham chiếu cố ý chừa một khoảng
    # border_band để chính nét viền không bị tính ngược vào mẫu nền so sánh.
    boundary_mask = _ring_mask(
        rgb.size,
        (left - border_band, top - border_band,
         right + border_band, bottom + border_band),
        (left + border_band, top + border_band,
         right - border_band, bottom - border_band),
    )
    inside_mask = _box_mask(
        rgb.size,
        (left + 2 * border_band, top + 2 * border_band,
         right - 2 * border_band, bottom - 2 * border_band),
    )
    outside_mask = _ring_mask(
        rgb.size,
        (left - 5 * border_band, top - 5 * border_band,
         right + 5 * border_band, bottom + 5 * border_band),
        (left - 2 * border_band, top - 2 * border_band,
         right + 2 * border_band, bottom + 2 * border_band),
    )

    edge = _edge_density(edges, inside_mask)
    outside_edge = _edge_density(edges, outside_mask)
    boundary_edge = _edge_density(edges, boundary_mask)
    inside_stat = ImageStat.Stat(rgb, inside_mask)
    outside_stat = ImageStat.Stat(rgb, outside_mask)
    std = sum(inside_stat.stddev) / 3
    outside_std = sum(outside_stat.stddev) / 3

    side_distances = _side_color_distances(rgb, box, color_band)
    mean_distance = sum(side_distances) / len(side_distances)
    jumped_sides = sum(distance >= 18 for distance in side_distances)

    boundary_suspicious = (
        boundary_edge >= 0.055
        and boundary_edge >= max(0.01, edge, outside_edge) * 1.8
    )
    panel_suspicious = jumped_sides >= 2
    content_suspicious = (
        edge >= 0.09
        or (edge >= 0.06 and edge >= max(0.01, outside_edge) * 0.75)
        or std >= 38
        or (std >= 28 and std >= max(1.0, outside_std) * 0.75)
    )
    return EmptyRegionMeasurement(
        empty=not (boundary_suspicious or panel_suspicious or content_suspicious),
        edge_density=edge,
        outside_edge_density=outside_edge,
        color_stddev=std,
        outside_color_stddev=outside_std,
        mean_color_distance=mean_distance,
        boundary_edge_density=boundary_edge,
        boundary_violation=boundary_suspicious,
        flat_panel_violation=panel_suspicious,
        content_violation=content_suspicious,
    )
