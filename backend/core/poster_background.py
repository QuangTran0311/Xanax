"""Đo xem model có thật sự chừa vùng dán sản phẩm hay không."""
from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageStat

from core.poster_templates import NormalizedRegion


@dataclass(frozen=True)
class EmptyRegionMeasurement:
    empty: bool
    edge_density: float
    outside_edge_density: float
    color_stddev: float
    outside_color_stddev: float
    mean_color_distance: float

    def log_summary(self) -> str:
        return (
            f"empty={self.empty}, edge={self.edge_density:.3f} "
            f"(ngoài={self.outside_edge_density:.3f}), std={self.color_stddev:.1f} "
            f"(ngoài={self.outside_color_stddev:.1f}), lệch_màu={self.mean_color_distance:.1f}"
        )


def _pixel_box(size: tuple[int, int], region: NormalizedRegion) -> tuple[int, int, int, int]:
    width, height = size
    return (
        max(0, min(width - 1, round(region.left * width))),
        max(0, min(height - 1, round(region.top * height))),
        max(1, min(width, round(region.right * width))),
        max(1, min(height, round(region.bottom * height))),
    )


def _edge_density(gray: Image.Image, mask: Image.Image) -> float:
    # FIND_EDGES tạo viền giả ở mép ảnh, nên xóa 2 px ngoài cùng trước khi đếm.
    edges = gray.filter(ImageFilter.FIND_EDGES).point(lambda value: 255 if value >= 28 else 0)
    clean_mask = mask.copy()
    if clean_mask.width > 4 and clean_mask.height > 4:
        clean_mask.paste(0, (0, 0, clean_mask.width, 2))
        clean_mask.paste(0, (0, clean_mask.height - 2, clean_mask.width, clean_mask.height))
        clean_mask.paste(0, (0, 0, 2, clean_mask.height))
        clean_mask.paste(0, (clean_mask.width - 2, 0, clean_mask.width, clean_mask.height))
    count = ImageStat.Stat(clean_mask).sum[0] / 255
    if count <= 0:
        return 0.0
    return (ImageStat.Stat(edges, clean_mask).sum[0] / 255) / count


def measure_empty_product_region(
    image: Image.Image, region: NormalizedRegion,
) -> EmptyRegionMeasurement:
    """So vùng chừa với phần poster còn lại bằng biên và độ phân tán màu.

    Ngưỡng được chọn để nền gradient/texture nhẹ vẫn đạt: độ lệch chuẩn dưới 28,
    mật độ biên dưới 6% và lệch màu trung bình dưới 30 đều được coi là nền. Một
    vùng bị vẽ vật thể bị loại ngay nếu std >= 38, biên >= 9%, hoặc màu trung bình
    lệch phần còn lại >= 30; ở khoảng giữa chỉ loại khi số đo còn lớn ít nhất 75%
    phần ngoài. Tín hiệu lệch màu bắt riêng ca vật thể màu phẳng tô kín cả ô — ca
    mà biên và std bên trong đều gần 0. Các mốc được kiểm chứng bằng ảnh giả trong
    test: nền trơn/gradient đạt, còn khối vật thể tương phản thì trượt.
    """
    rgb = image.convert("RGB")
    gray = rgb.convert("L")
    box = _pixel_box(rgb.size, region)

    inside_mask = Image.new("L", rgb.size, 0)
    inside_mask.paste(255, box)
    outside_mask = Image.new("L", rgb.size, 255)
    outside_mask.paste(0, box)

    edge = _edge_density(gray, inside_mask)
    outside_edge = _edge_density(gray, outside_mask)
    inside_stat = ImageStat.Stat(rgb, inside_mask)
    outside_stat = ImageStat.Stat(rgb, outside_mask)
    std = sum(inside_stat.stddev) / 3
    outside_std = sum(outside_stat.stddev) / 3
    mean_distance = sum(
        abs(inside - outside)
        for inside, outside in zip(inside_stat.mean, outside_stat.mean)
    ) / 3

    edge_suspicious = edge >= 0.09 or (
        edge >= 0.06 and edge >= max(0.01, outside_edge) * 0.75
    )
    color_suspicious = std >= 38 or (
        std >= 28 and std >= max(1.0, outside_std) * 0.75
    )
    contrast_suspicious = mean_distance >= 30
    return EmptyRegionMeasurement(
        empty=not (edge_suspicious or color_suspicious or contrast_suspicious),
        edge_density=edge,
        outside_edge_density=outside_edge,
        color_stddev=std,
        outside_color_stddev=outside_std,
        mean_color_distance=mean_distance,
    )
