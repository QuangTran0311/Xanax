"""MCP server: cắt ảnh sản phẩm.

Lấp khoảng trống của rembg-mcp — nó chỉ tách nền (trả PNG trong suốt nhưng giữ
nguyên khung ảnh gốc), không cắt sát sản phẩm. Server này gộp cả chuỗi:

    tách nền → cắt sát viền sản phẩm → chừa lề → đưa về tỉ lệ khung bài đăng

Server được gọi qua target ổn định ``xanax://image-cut``. Xanax dùng Python của
venv chính để chạy ``image_cut_launcher.py``; launcher ưu tiên biến môi trường
``XANAX_REMBG_PYTHON``, rồi tìm Python ở vị trí venv rembg mặc định của từng hệ
điều hành và mới chạy file này. Venv rembg phải có rembg + Pillow + mcp và tách
riêng khỏi venv chính; xem deploy/README.md.

Model mặc định là birefnet-general-lite. Đo trên hai ảnh chụp thật (móc khoá đà
điểu len, một tấm treo trên ba lô tối màu, một tấm đặt trên bàn gỗ sáng), nó là
model duy nhất xử lý được cả hai:

    u2netp thô          còn quầng nền dày quanh sản phẩm
    u2netp + matting    sạch nền tối, nhưng BÓNG ĐỔ trên bàn gỗ vẫn dính nguyên,
                       và matting làm bạc mất con mắt đen
    isnet-general-use   tệ hơn u2netp, còn rắc pixel lạc khắp khung
    birefnet-general-lite
                       sạch cả hai ảnh, mắt đen giữ nguyên, tự loại được bóng đổ
                       và phần lớn vòng khoá kim loại

Đo production ngày 18/08/2026: birefnet mất 24–46 giây/ảnh, u2netp mất
0,7–2,3 giây/ảnh. Với ảnh đăng bán thì chất lượng birefnet đáng để chờ. Cần nhanh
thì đổi model='u2netp' và chấp nhận bóng đổ còn sót.

Vì sao bóng đổ không chữa được bằng tham số, xem docs/tach-nen-san-pham.md.
"""
from __future__ import annotations

import ctypes
import gc
import io
import os
import sys
import threading
from pathlib import Path

from mcp.server.fastmcp import FastMCP
import onnxruntime as ort
from PIL import Image
from rembg import new_session, remove

# Khi chạy file này trực tiếp, Python đặt sys.path[0] là thư mục chứa script
# (backend/mcp_servers), không phải cwd; launcher chdir về backend vẫn chưa đủ
# để import gói mcp_servers.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from mcp_servers.image_cut_helpers import (
    IDLE_SECONDS_ENV,
    MAX_SIDE_ENV,
    InsufficientMemoryError,
    apply_alpha_to_original,
    calculate_inference_size,
    memory_check_error,
    read_nonnegative_env,
    skip_memory_check,
)

mcp = FastMCP("xanax-image-cut")

# Session được cache theo model trong một đợt làm việc: nạp model là phần đắt
# nhất (~4s cho u2netp), nhưng giữ nó suốt đêm từng làm RSS nằm ở vài GB.
_sessions: dict[str, object] = {}
_sessions_lock = threading.Lock()
_idle_timer: threading.Timer | None = None
_idle_generation = 0
_active_cuts = 0

# Alpha dưới ngưỡng này coi như nền. Không lọc thì các pixel bán trong suốt còn
# sót quanh biên sẽ làm bounding box phình ra, cắt không sát.
_ALPHA_THRESHOLD = 12

_SUPPORTED_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")

_MEMINFO_PATH = Path("/proc/meminfo")
_CGROUP_MEMORY_MAX_PATH = Path("/sys/fs/cgroup/memory.max")
_CGROUP_MEMORY_CURRENT_PATH = Path("/sys/fs/cgroup/memory.current")


def _read_optional_text(path: Path) -> str | None:
    """Đọc pseudo-file Linux; dev Windows/cgroup v1 không có file thì bỏ qua."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _ensure_memory_available(model: str) -> None:
    """Lớp I/O mỏng quanh logic thuần trong image_cut_helpers."""
    if skip_memory_check():
        return
    error = memory_check_error(
        model,
        _read_optional_text(_MEMINFO_PATH),
        _read_optional_text(_CGROUP_MEMORY_MAX_PATH),
        _read_optional_text(_CGROUP_MEMORY_CURRENT_PATH),
    )
    if error:
        raise InsufficientMemoryError(error)


def _session(model: str):
    with _sessions_lock:
        if model not in _sessions:
            session_options = ort.SessionOptions()
            # Arena nhanh hơn một chút vì tái dùng vùng đã cấp phát, nhưng cũng là
            # lý do RSS leo lên rồi giữ nguyên sau inference trên VPS 5,8 GB.
            session_options.enable_cpu_mem_arena = False
            try:
                _sessions[model] = new_session(model, sess_opts=session_options)
            except TypeError:
                # Một số bản rembg cũ chưa nhận sess_opts. stderr là bắt buộc vì
                # stdout của tiến trình này chỉ dành cho JSON-RPC của MCP.
                print(
                    "Cảnh báo: rembg không nhận sess_opts; CPU memory arena vẫn được bật.",
                    file=sys.stderr,
                    flush=True,
                )
                _sessions[model] = new_session(model)
        return _sessions[model]


def _release_process_memory() -> None:
    """Dọn object Python rồi xin glibc trả các heap page rảnh về hệ điều hành."""
    gc.collect()
    if not sys.platform.startswith("linux"):
        return
    try:
        libc = ctypes.CDLL("libc.so.6")
        malloc_trim = libc.malloc_trim
        malloc_trim.argtypes = [ctypes.c_size_t]
        malloc_trim.restype = ctypes.c_int
        malloc_trim(0)
    except (OSError, AttributeError):
        # Windows dev và musl/Alpine không có entry point này; dọn GC vẫn đủ để
        # chạy đúng, chỉ không ép allocator trả RSS ngay được.
        pass


def _drop_sessions_after_idle(generation: int) -> None:
    global _idle_timer
    with _sessions_lock:
        if generation != _idle_generation or _active_cuts:
            return
        _sessions.clear()
        _idle_timer = None
    # Lần cắt sau thời gian nhàn rỗi phải nạp lại model (~4s), đổi lại tiến trình
    # MCP không giữ vài GB suốt đêm chỉ để tránh lần nạp đó.
    _release_process_memory()


def _cut_started() -> None:
    global _active_cuts, _idle_generation, _idle_timer
    with _sessions_lock:
        _active_cuts += 1
        _idle_generation += 1
        if _idle_timer is not None:
            _idle_timer.cancel()
            _idle_timer = None


def _cut_finished() -> None:
    global _active_cuts, _idle_generation, _idle_timer
    idle_seconds = read_nonnegative_env(IDLE_SECONDS_ENV, 600)
    with _sessions_lock:
        _active_cuts -= 1
        if _active_cuts or idle_seconds == 0:
            return
        _idle_generation += 1
        generation = _idle_generation
        timer = threading.Timer(
            idle_seconds, _drop_sessions_after_idle, args=(generation,),
        )
        timer.daemon = True
        _idle_timer = timer
        timer.start()


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
    fg_threshold: int = 240, bg_threshold: int = 10, erode_size: int = 10,
) -> dict:
    _ensure_memory_available(model)
    _cut_started()
    try:
        return _cut_one_impl(
            input_path, output_path, model, padding_percent, ratio, background,
            alpha_matting, fg_threshold, bg_threshold, erode_size,
        )
    finally:
        # Tách hàm impl để frame chứa các buffer ảnh đã biến mất trước lúc trim;
        # nếu gc chạy ngay trong cùng frame thì chính local variable còn giữ RAM.
        _release_process_memory()
        _cut_finished()


def _cut_one_impl(
    input_path: str, output_path: str, model: str, padding_percent: float,
    ratio: str, background: str, alpha_matting: bool,
    fg_threshold: int = 240, bg_threshold: int = 10, erode_size: int = 10,
) -> dict:
    src = Path(input_path)
    if not src.is_file():
        raise FileNotFoundError(f"Không tìm thấy ảnh: {input_path}")

    ratio_value = _parse_ratio(ratio)
    bg_rgba = _parse_background(background)

    remove_options = {
        "session": _session(model),
        "alpha_matting": alpha_matting,
        "alpha_matting_foreground_threshold": fg_threshold,
        "alpha_matting_background_threshold": bg_threshold,
        "alpha_matting_erode_size": erode_size,
    }
    max_side = read_nonnegative_env(MAX_SIDE_ENV, 2000)
    with Image.open(src) as original:
        original_size = original.size
        inference_size = calculate_inference_size(original_size, max_side)
        if inference_size is None:
            # Ảnh đã nhỏ thì giữ nguyên đường đi cũ, kể cả cách rembg giải mã bytes.
            cut_bytes = remove(src.read_bytes(), **remove_options)
            with Image.open(io.BytesIO(cut_bytes)) as removed:
                cut = removed.convert("RGBA")
        else:
            # Model vốn resize nội bộ (birefnet về 1024x1024), nên bước này hầu
            # như không làm mask xấu đi; phần tiết kiệm lớn là buffer matting và
            # hậu xử lý không còn được dựng ở độ phân giải điện thoại 4000x3000.
            inference = original.convert("RGB").resize(
                inference_size, Image.Resampling.LANCZOS,
            )
            inference_bytes = io.BytesIO()
            inference.save(inference_bytes, format="PNG")
            cut_bytes = remove(inference_bytes.getvalue(), **remove_options)
            with Image.open(io.BytesIO(cut_bytes)) as removed:
                # Không dùng only_mask: đường đó bỏ qua alpha matting mà public
                # tool đang cho phép bật. Alpha phải lấy từ kết quả RGBA đầy đủ.
                alpha = removed.convert("RGBA").getchannel("A")
            cut = apply_alpha_to_original(original, alpha)

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
    model: str = "birefnet-general-lite",
    padding_percent: float = 2.0,
    ratio: str = "",
    background: str = "transparent",
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
) -> str:
    """Tách nền và cắt sát sản phẩm trong ảnh, xuất ra ảnh đã cắt.

    input_path: đường dẫn tuyệt đối tới ảnh gốc.
    output_path: đường dẫn tuyệt đối tới file kết quả (.png để giữ nền trong suốt).
    model: birefnet-general-lite (mặc định, sạch nhất, production đo 24–46s/ảnh),
        u2netp (production đo 0,7–2,3s/ảnh nhưng để sót bóng đổ), u2net,
        isnet-general-use (đã đo: tệ hơn
        u2netp, đừng dùng), u2net_cloth_seg (quần áo), u2net_human_seg (người).
    padding_percent: lề chừa quanh sản phẩm, tính theo % kích thước sản phẩm.
    ratio: tỉ lệ khung kết quả như '1:1', '4:5', '16:9'. Bỏ trống thì cắt sát sản phẩm.
    background: 'transparent' hoặc mã hex như '#ffffff'.
    alpha_matting: tính lại độ trong suốt ở vành biên dựa trên MÀU thật của pixel,
        thay vì tin mask của model. Với birefnet thì không cần — mask nó đã đủ
        sạch, bật lên chỉ tốn thêm ~4s. Cần khi dùng u2netp trên nền lộn xộn: đo
        được giảm hơn nửa số pixel nền còn dính (5.366 xuống 2.712). Nhưng nó
        phân biệt bằng MÀU, nên có thể làm bạc những chi tiết tối nằm sát biên —
        đã thấy nó làm nhạt mất một con mắt đen của sản phẩm.
    alpha_matting_foreground_threshold: trên ngưỡng này coi là chắc chắn sản phẩm.
    alpha_matting_background_threshold: dưới ngưỡng này coi là chắc chắn nền. Nâng
        lên 30-50 nếu nền tối mà vẫn sót.
    alpha_matting_erode_size: bào mòn bao nhiêu pixel ở mép mask để đẩy vào diện
        "xét lại theo màu". ĐỪNG nâng quá 10 — đo trên ảnh thật, để 25 thì vệt nền
        sạch hơn chút nhưng thuật toán ăn mất luôn con mắt đen của sản phẩm.
    """
    try:
        info = _cut_one(
            input_path, output_path, model, padding_percent, ratio,
            background, alpha_matting, alpha_matting_foreground_threshold,
            alpha_matting_background_threshold, alpha_matting_erode_size,
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
    model: str = "birefnet-general-lite",
    padding_percent: float = 2.0,
    ratio: str = "",
    background: str = "transparent",
    alpha_matting: bool = False,
) -> str:
    """Cắt sản phẩm cho toàn bộ ảnh trong một thư mục.

    Tham số giống cut_product. Kết quả lưu cùng tên file, đuôi .png.

    Trên production, model mặc định birefnet-general-lite tốn 24–46s/ảnh. Thư
    mục vài trăm ảnh thì cân nhắc model='u2netp' (0,7–2,3s/ảnh) và chấp nhận
    bóng đổ sót.
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

    # Chặn ngay trước vòng lặp để một batch lớn không trả cùng lỗi OOM hàng trăm lần.
    try:
        _ensure_memory_available(model)
    except InsufficientMemoryError as exc:
        return f"Lỗi: {exc}"

    done, errors = 0, []
    for image in images:
        try:
            _cut_one(
                str(image), str(Path(output_folder) / f"{image.stem}.png"),
                model, padding_percent, ratio, background, alpha_matting,
            )
            done += 1
        except InsufficientMemoryError as exc:
            return (
                f"Đã dừng sớm sau {done}/{len(images)} ảnh vì RAM không còn đủ. "
                f"Lỗi: {exc}"
            )
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
