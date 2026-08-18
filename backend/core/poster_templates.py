"""Bộ layout cho poster dùng ảnh sản phẩm thật.

Module này chỉ chứa dữ liệu và phép tra cứu, không đọc file hay gọi model. Vì mọi
template nằm trong ``_TEMPLATES``, thêm một layout mới không buộc luồng sinh ảnh
hoặc luồng ghép phải biết thêm một nhánh ``if`` nào.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedRegion:
    """Hình chữ nhật theo tỷ lệ 0–1: trái, trên, phải, dưới."""

    left: float
    top: float
    right: float
    bottom: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return self.left, self.top, self.right, self.bottom


@dataclass(frozen=True)
class PosterTemplate:
    code: str
    use_when: str
    product_region: NormalizedRegion
    design_regions: tuple[str, ...]

    def prompt_description(self) -> str:
        """Mô tả ổn định để cả skill và prompt siết lần hai dùng cùng tọa độ."""
        r = self.product_region
        return (
            f"Vùng sản phẩm: x {r.left:.0%}–{r.right:.0%}, "
            f"y {r.top:.0%}–{r.bottom:.0%}. "
            + " ".join(self.design_regions)
        )


DEFAULT_TEMPLATE_CODE = "giua-khung"

# Nguồn dữ liệu duy nhất của các layout. Nơi khác chỉ gọi get_template(), vì vậy
# thêm template mới ở đây là đủ để parser, phép đo và bộ ghép cùng hiểu nó.
_TEMPLATES: dict[str, PosterTemplate] = {
    "giua-khung": PosterTemplate(
        code="giua-khung",
        use_when="Món cao và hẹp như móc khóa hoặc búp bê.",
        product_region=NormalizedRegion(0.30, 0.22, 0.70, 0.74),
        design_regions=(
            "Tiêu đề ở dải trên.",
            "Đặt 2–3 thẻ tính năng trong dải y 74%–88%.",
            "Thanh CTA nằm trong dải y 88%–97%.",
        ),
    ),
    "trai-san-pham": PosterTemplate(
        code="trai-san-pham",
        use_when="Cần khoe nhiều tính năng và dành riêng một cột thông tin.",
        product_region=NormalizedRegion(0.06, 0.26, 0.56, 0.84),
        design_regions=(
            "Tiêu đề dùng toàn chiều ngang trong dải y 0%–24%.",
            "Cột 3 thẻ bên phải ở x 58%–96%, y 26%–84%.",
            "Thanh CTA nằm trong dải y 86%–97%.",
        ),
    ),
    "luoi-the-duoi": PosterTemplate(
        code="luoi-the-duoi",
        use_when="Món bè ngang như bộ lót ly hoặc khăn.",
        product_region=NormalizedRegion(0.22, 0.20, 0.78, 0.58),
        design_regions=(
            "Tiêu đề nằm trong dải y 0%–18%.",
            "Hàng 4 thẻ nhỏ nằm trong dải y 60%–76%.",
            "Ghi chú nằm trong dải y 76%–86%.",
            "Thanh CTA nằm trong dải y 87%–97%.",
        ),
    ),
}


def get_template(code: str | None) -> PosterTemplate:
    """Tra template; mã thiếu hoặc lạ lùi về mặc định để pipeline không sập."""
    normalized = (code or "").strip().lower()
    return _TEMPLATES.get(normalized, _TEMPLATES[DEFAULT_TEMPLATE_CODE])


def template_codes() -> tuple[str, ...]:
    return tuple(_TEMPLATES)
