"""MCP server: cắt ảnh sản phẩm.

Lấp khoảng trống của rembg-mcp — nó chỉ tách nền (trả PNG trong suốt nhưng giữ
nguyên khung ảnh gốc), không cắt sát sản phẩm. Server này gộp cả chuỗi:

    tách nền → cắt sát viền sản phẩm → chừa lề → đưa về tỉ lệ khung bài đăng

Chạy bằng Python của venv rembg (đã có rembg + Pillow + mcp), không phải venv
của xanax:

    C:\\Users\\Quang\\.claude\\mcp-servers\\rembg-mcp\\.venv\\Scripts\\python.exe
    d:\\xanax\\mcp_servers\\image_cut.py

Model mặc định là u2netp: đo trên máy này nhanh gấp đôi u2net (0.44s so với
0.97s), nhẹ hơn ~330MB RAM, và cho viền sạch hơn trên ảnh sản phẩm nền phẳng.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from PIL import Image
from rembg import new_session, remove

mcp = FastMCP("xanax-image-cut")

# Session được cache theo model: nạp model là phần đắt nhất (~4s cho u2netp),
# giữ lại để từ ảnh thứ hai trở đi chỉ còn thời gian inference.
_sessions: dict[str, object] = {}

# Alpha dưới ngưỡng này coi như nền. Không lọc thì các pixel bán trong suốt còn
# sót quanh biên sẽ làm bounding box phình ra, cắt không sát.
_ALPHA_THRESHOLD = 12

_SUPPORTED_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")


def _session(model: str):
    if model not in _sessions:
        _sessions[model] = new_session(model)
    return _sessions[model]


def _parse_ratio(ratio: str) -> float | None:
    """'4:5' → 0.8. Chuỗi rỗng → None (giữ nguyên khung sát sản phẩm)."""
    ratio = (ratio or "").strip()
    if not ratio:
        return None
    sep = ":" if ":" in ratio else "/" if "/" in ratio else None
    if sep is None:
        raise ValueError(f"Tỉ lệ không hợp lệ: {ratio!r}. Dùng dạng '1:1', '4:5', '16:9'.")
    w, h = ratio.split(sep, 1)
    w_val, h_val = float(w), float(h)
    if w_val <= 0 or h_val <= 0:
        raise ValueError(f"Tỉ lệ phải là số dương: {ratio!r}")
    return w_val / h_val


def _parse_background(background: str) -> tuple[int, int, int, int]:
    """'transparent' hoặc mã hex '#ffffff' → RGBA."""
    value = (background or "transparent").strip().lower()
    if value in ("transparent", "none", ""):
        return (0, 0, 0, 0)
    hex_value = value.lstrip("#")
    if len(hex_value) == 3:
        hex_value = "".join(c * 2 for c in hex_value)
    if len(hex_value) != 6:
        raise ValueError(
            f"Màu nền không hợp lệ: {background!r}. Dùng 'transparent' hoặc hex '#ffffff'.",
        )
    try:
        r, g, b = (int(hex_value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        raise ValueError(f"Màu nền không hợp lệ: {background!r}") from None
    return (r, g, b, 255)


def _alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    alpha = image.getchannel("A").point(lambda v: 255 if v >= _ALPHA_THRESHOLD else 0)
    return alpha.getbbox()


def _cut_one(
    input_path: str, output_path: str, model: str, padding_percent: float,
    ratio: str, background: str, alpha_matting: bool,
) -> dict:
    src = Path(input_path)
    if not src.is_file():
        raise FileNotFoundError(f"Không tìm thấy ảnh: {input_path}")

    ratio_value = _parse_ratio(ratio)
    bg_rgba = _parse_background(background)

    original = Image.open(src)
    original_size = original.size

    cut_bytes = remove(
        src.read_bytes(), session=_session(model), alpha_matting=alpha_matting,
    )
    cut = Image.open(io.BytesIO(cut_bytes)).convert("RGBA")

    bbox = _alpha_bbox(cut)
    if bbox is None:
        raise ValueError(
            "Không tìm thấy sản phẩm trong ảnh — toàn bộ ảnh bị coi là nền. "
            f"Thử model khác (hiện dùng {model!r}).",
        )
    product = cut.crop(bbox)

    pad = max(0.0, padding_percent) / 100.0
    if ratio_value is None:
        # Không ép tỉ lệ: chỉ nới đều 4 phía quanh sản phẩm.
        margin_x = round(product.width * pad)
        margin_y = round(product.height * pad)
        canvas_size = (product.width + margin_x * 2, product.height + margin_y * 2)
    else:
        # Ép tỉ lệ: sản phẩm chiếm phần khung còn lại sau khi trừ lề.
        scale = 1.0 + pad * 2
        need_w, need_h = product.width * scale, product.height * scale
        if need_w / need_h >= ratio_value:
            canvas_w = need_w
            canvas_h = canvas_w / ratio_value
        else:
            canvas_h = need_h
            canvas_w = canvas_h * ratio_value
        canvas_size = (max(1, round(canvas_w)), max(1, round(canvas_h)))

    canvas = Image.new("RGBA", canvas_size, bg_rgba)
    offset = (
        (canvas_size[0] - product.width) // 2,
        (canvas_size[1] - product.height) // 2,
    )
    canvas.paste(product, offset, product)

    dst = Path(output_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.suffix.lower() in (".jpg", ".jpeg"):
        if bg_rgba[3] == 0:
            raise ValueError(
                "JPG không lưu được nền trong suốt. Đổi đuôi sang .png hoặc đặt "
                "background thành mã màu, ví dụ '#ffffff'.",
            )
        canvas.convert("RGB").save(dst, quality=95)
    else:
        canvas.save(dst)

    return {
        "output_path": str(dst),
        "original_size": f"{original_size[0]}x{original_size[1]}",
        "product_bbox": list(bbox),
        "product_size": f"{product.width}x{product.height}",
        "output_size": f"{canvas_size[0]}x{canvas_size[1]}",
    }


@mcp.tool()
def cut_product(
    input_path: str,
    output_path: str,
    model: str = "u2netp",
    padding_percent: float = 2.0,
    ratio: str = "",
    background: str = "transparent",
    alpha_matting: bool = False,
) -> str:
    """Tách nền và cắt sát sản phẩm trong ảnh, xuất ra ảnh đã cắt.

    input_path: đường dẫn tuyệt đối tới ảnh gốc.
    output_path: đường dẫn tuyệt đối tới file kết quả (.png để giữ nền trong suốt).
    model: u2netp (mặc định, nhanh nhất), u2net, isnet-general-use,
        birefnet-general-lite, u2net_cloth_seg (quần áo), u2net_human_seg (người).
    padding_percent: lề chừa quanh sản phẩm, tính theo % kích thước sản phẩm.
    ratio: tỉ lệ khung kết quả như '1:1', '4:5', '16:9'. Bỏ trống thì cắt sát sản phẩm.
    background: 'transparent' hoặc mã hex như '#ffffff'.
    alpha_matting: bật để biên mượt hơn với tóc/vật thể trong suốt, chậm hơn nhiều.
    """
    try:
        info = _cut_one(
            input_path, output_path, model, padding_percent, ratio,
            background, alpha_matting,
        )
    except Exception as exc:
        return f"Lỗi: {exc}"
    return (
        f"Đã cắt xong: {info['output_path']}\n"
        f"Ảnh gốc {info['original_size']} → sản phẩm tại {info['product_bbox']} "
        f"({info['product_size']}) → kết quả {info['output_size']}"
    )


@mcp.tool()
def cut_product_batch(
    input_folder: str,
    output_folder: str,
    model: str = "u2netp",
    padding_percent: float = 2.0,
    ratio: str = "",
    background: str = "transparent",
) -> str:
    """Cắt sản phẩm cho toàn bộ ảnh trong một thư mục.

    Tham số giống cut_product. Kết quả lưu cùng tên file, đuôi .png.
    """
    src_dir = Path(input_folder)
    if not src_dir.is_dir():
        return f"Lỗi: không tìm thấy thư mục {input_folder}"

    images = sorted(
        p for p in src_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _SUPPORTED_EXT
    )
    if not images:
        return f"Không có ảnh nào trong {input_folder}"

    done, errors = 0, []
    for image in images:
        try:
            _cut_one(
                str(image), str(Path(output_folder) / f"{image.stem}.png"),
                model, padding_percent, ratio, background, False,
            )
            done += 1
        except Exception as exc:
            errors.append(f"{image.name}: {exc}")

    lines = [f"Đã cắt {done}/{len(images)} ảnh vào {output_folder} (model {model})"]
    if errors:
        lines.append("Lỗi:")
        lines.extend(f"  - {e}" for e in errors)
    return "\n".join(lines)


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "4")
    mcp.run()
