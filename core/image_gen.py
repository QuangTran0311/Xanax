"""
Image generation — gọi OpenAI-compatible /images/generations endpoint,
lưu ảnh thẳng vào thư mục archive của lần chạy quy trình (core/project_storage.py).
"""
from __future__ import annotations

import base64
import logging
import re
from pathlib import Path

import httpx

logger = logging.getLogger("xanax.image_gen")

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

# Aspect ratio → (ratio_w, ratio_h) for post-processing
_RATIO_MAP = {
    "1:1":  (1, 1),
    "4:5":  (4, 5),
    "9:16": (9, 16),
    "16:9": (16, 9),
}


def _fit_to_ratio(img, ratio_w: int, ratio_h: int):
    """Pad image to target ratio using blurred + darkened background fill."""
    from PIL import Image, ImageFilter, ImageEnhance

    w, h = img.size
    target_aspect = ratio_w / ratio_h
    current_aspect = w / h

    if abs(current_aspect - target_aspect) < 0.02:
        return img

    if current_aspect > target_aspect:
        new_w, new_h = w, int(w * ratio_h / ratio_w)
    else:
        new_w, new_h = int(h * ratio_w / ratio_h), h

    # Blurred + darkened version of original as background
    bg = img.resize((new_w, new_h), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
    bg = ImageEnhance.Brightness(bg).enhance(0.35)

    # Paste original centered
    x_off = (new_w - w) // 2
    y_off = (new_h - h) // 2
    bg.paste(img, (x_off, y_off))
    return bg


def _add_gradient_text(img, text: str):
    """Overlay gradient + styled text at bottom of image."""
    from PIL import Image, ImageDraw, ImageFont

    img = img.convert("RGBA")
    w, h = img.size

    # Gradient: transparent → dark, bottom 38% of image
    grad_h = int(h * 0.38)
    gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gradient)
    for i in range(grad_h):
        alpha = int(210 * (i / grad_h) ** 1.4)
        y = h - grad_h + i
        gd.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    img = Image.alpha_composite(img, gradient)

    # Load font
    font_size = max(52, w // 13)
    font = None
    for fc in _FONT_CANDIDATES:
        try:
            font = ImageFont.truetype(fc, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    # Word wrap
    draw = ImageDraw.Draw(img)
    words = text.split()
    lines: list[str] = []
    current = ""
    max_w = int(w * 0.82)
    for word in words:
        test = (current + " " + word).strip()
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_h = font_size + 14
    total_h = len(lines) * line_h
    margin_bottom = int(h * 0.055)
    y_start = h - margin_bottom - total_h

    for i, line in enumerate(lines):
        bb = draw.textbbox((0, 0), line, font=font)
        text_w = bb[2] - bb[0]
        x = (w - text_w) // 2
        y = y_start + i * line_h

        # Multi-layer shadow for depth
        for dx, dy, alpha in [(3, 3, 200), (-2, -2, 120), (0, 4, 160)]:
            draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, alpha))
        # Main white text
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    return img.convert("RGB")


def _build_image_url(base_url: str) -> str:
    """Build /images/generations URL — tolerates base_url already containing the endpoint."""
    base = base_url.rstrip("/")
    if base.endswith("/images/generations"):
        return base
    if base.endswith("/v1"):
        return base + "/images/generations"
    return base + "/v1/images/generations"


def extract_image_prompt(llm_output: str) -> str | None:
    """Parse IMAGE PROMPT block từ output Lexapro (GPT-style natural language prompt)."""
    # Thử IMAGE PROMPT trước (format mới cho GPT-image models)
    match = re.search(
        r"IMAGE PROMPT\s*\n(.*?)(?:\n(?:TỶ LỆ|RATIO|---|\Z))",
        llm_output,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    # Fallback: lấy toàn bộ content sau "IMAGE PROMPT" đến hết
    match = re.search(r"IMAGE PROMPT\s*\n(.+)", llm_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def extract_positive_prompt(llm_output: str) -> str | None:
    """Legacy: Parse POSITIVE PROMPT block (Stable Diffusion format)."""
    match = re.search(
        r"POSITIVE PROMPT\s*\n(.*?)(?:\nNEGATIVE PROMPT|\nHƯỚNG DẪN|\nTEXT OVERLAY|\Z)",
        llm_output,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return None


def extract_image_ratio(llm_output: str) -> tuple[int, int]:
    """Parse tỷ lệ từ output Lexapro. Mặc định 4:5 (Facebook Feed)."""
    match = re.search(r"Tỷ lệ[:\s]+(\d+:\d+)", llm_output, re.IGNORECASE)
    if match:
        ratio = match.group(1).strip()
        return _RATIO_MAP.get(ratio, (4, 5))
    return (4, 5)


def extract_text_overlay(llm_output: str) -> str | None:
    """Parse TEXT OVERLAY block từ output Lexapro."""
    match = re.search(
        r"TEXT OVERLAY\s*\n(.*?)(?:\n[📍#A-Z\U0001F300-\U0001FFFF]|\Z)",
        llm_output,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        for line in match.group(1).splitlines():
            line = line.strip()
            if line and not line.startswith("-"):
                return line
    return None


class ImageGenError(Exception):
    """Raised when image generation fails with a human-readable reason."""


async def generate_image(
    prompt: str,
    base_url: str,
    api_key: str,
    model: str,
    save_path: Path,
    ratio: tuple[int, int] = (4, 5),
    usage_state: dict | None = None,
) -> Path:
    """
    Gọi /images/generations, post-process sang đúng tỷ lệ, lưu vào save_path
    (caller quyết định thư mục/tên file — xem core/project_storage.py).
    Trả về save_path. Nếu provider trả usage, cập nhật usage_state để caller ghi
    dashboard. Raises ImageGenError với thông báo cụ thể khi thất bại.
    """
    from PIL import Image
    import io

    url = _build_image_url(base_url)
    payload = {"model": model, "prompt": prompt, "n": 1}

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            if not resp.is_success:
                try:
                    body = resp.json()
                    detail = body.get("error", {}).get("message") or body.get("detail") or resp.text[:300]
                except Exception:
                    detail = resp.text[:300]
                raise ImageGenError(f"HTTP {resp.status_code} từ image model: {detail}")

            data = resp.json()
            usage = data.get("usage") or {}
            if usage_state is not None and isinstance(usage, dict):
                input_details = (
                    usage.get("input_tokens_details")
                    or usage.get("prompt_tokens_details")
                    or {}
                )
                if not isinstance(input_details, dict):
                    input_details = {}
                usage_values = {
                    "tokens_in": usage.get(
                        "input_tokens", usage.get("prompt_tokens", 0)
                    ),
                    "tokens_out": usage.get(
                        "output_tokens", usage.get("completion_tokens", 0)
                    ),
                    "tokens_cache": input_details.get(
                        "cached_tokens", usage.get("cached_tokens", 0)
                    ),
                }
                for key, value in usage_values.items():
                    try:
                        usage_state[key] = int(value or 0)
                    except (TypeError, ValueError):
                        usage_state[key] = 0
                        logger.warning(
                            "Image model trả usage không hợp lệ cho %s: %r",
                            key,
                            value,
                        )

            items = data.get("data") or []
            if not items:
                raise ImageGenError(f"Model không trả về ảnh. Response: {str(data)[:200]}")
            item = items[0]

            if item.get("b64_json"):
                img_bytes = base64.b64decode(item["b64_json"])
            elif item.get("url"):
                img_resp = await client.get(item["url"], timeout=60)
                img_resp.raise_for_status()
                img_bytes = img_resp.content
            else:
                raise ImageGenError(f"Response không có b64_json hoặc url. Keys: {list(item.keys())}")

        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        ratio_w, ratio_h = ratio
        img = _fit_to_ratio(img, ratio_w, ratio_h)

        save_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(save_path, "PNG", optimize=True)
        logger.info("Image saved: %s (%d:%d)", save_path, ratio_w, ratio_h)
        return save_path

    except ImageGenError:
        raise
    except httpx.TimeoutException:
        raise ImageGenError(f"Timeout sau 120s — model '{model}' không phản hồi (có thể không hỗ trợ image generation hoặc đang quá tải)")
    except Exception as exc:
        logger.exception("Image generation failed (model=%s, url=%s)", model, url)
        raise ImageGenError(f"Lỗi không xác định: {exc}")
