"""
Image generation — gọi OpenAI-compatible /images/generations endpoint,
lưu ảnh thẳng vào thư mục archive của lần chạy quy trình (core/project_storage.py).
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path

import httpx

logger = logging.getLogger("xanax.image_gen")

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
        r"IMAGE PROMPT\s*\n(.*?)(?:\n(?:TỶ LỆ|RATIO|ẢNH SẢN PHẨM|ANH SAN PHAM|PRODUCT IMAGE|---|\Z))",
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


def extract_template_code(llm_output: str) -> str:
    """Đọc mã trong khối TEMPLATE; thiếu/lạ đều dùng template mặc định.

    Việc lùi an toàn nằm ở module dữ liệu thay vì rải danh sách mã trong parser,
    nên thêm template mới không phải sửa hàm này.
    """
    match = re.search(
        r"^\s*TEMPLATE\s*:?\s*(?:\n\s*)?([^\s`]+)",
        llm_output or "", re.MULTILINE | re.IGNORECASE,
    )
    from core.poster_templates import get_template
    return get_template(match.group(1) if match else None).code


def extract_product_image(llm_output: str) -> str | None:
    """Đường dẫn ảnh sản phẩm đã tách nền, nếu nhân viên khai báo.

    Khối tuỳ chọn trong output, đứng cạnh IMAGE PROMPT và TỶ LỆ:

        ẢNH SẢN PHẨM
        D:\\xanax\\data\\assets\\abc_cut.png

    Có nó thì IMAGE PROMPT được hiểu là mô tả CÁI NỀN, còn sản phẩm là ảnh chụp
    thật dán lên (xem core/image_compose.py). Khai báo tường minh chứ không đoán
    "ảnh gần nhất trong phiên": đoán sai thì bài đăng mang ảnh một món hàng khác.
    """
    match = re.search(
        r"(?:ẢNH SẢN PHẨM|ANH SAN PHAM|PRODUCT IMAGE)\s*[:\n]\s*([^\n]+)",
        llm_output or "", re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip().strip("`\"'") or None


_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".heic", ".heif")


def attached_image_paths(message: str) -> list[str]:
    """Đường dẫn ảnh Papa đính kèm trong một tin nhắn của phòng chat.

    Giao diện chèn khối này vào cuối tin nhắn — nguồn duy nhất sinh ra nó là
    buildAttachmentBlock() trong frontend/src/components/ChatAttach.ts:

        <!-- FILE PAPA GỬI KÈM — đường dẫn tuyệt đối, dùng cho công cụ:
        - ostrich.jpg → D:\\xanax\\data\\assets\\ab12_ostrich.jpg
        -->

    Bóc ra ở phía server chứ không để nhân viên tự dò trong chữ: việc "có ảnh hay
    không" quyết định chọn chế độ A hay B, mà đó là chuyện phải chắc chắn. Nhân
    viên đọc lướt rồi bỏ sót một dòng là cả bài đăng đi sai đường.
    """
    block = re.search(r"<!--\s*FILE PAPA GỬI KÈM.*?-->", message or "",
                      re.DOTALL | re.IGNORECASE)
    if not block:
        return []
    paths = []
    for line in re.findall(r"^\s*-\s*.+?\s*→\s*(.+?)\s*$", block.group(0), re.MULTILINE):
        if line.lower().endswith(_IMAGE_EXT):
            paths.append(line)
    return paths


def latest_attached_images(history: list[dict]) -> list[str]:
    """Ảnh của lần đính kèm GẦN NHẤT trong cả cuộc trò chuyện.

    Quét cả lịch sử chứ không chỉ tin nhắn cuối: Papa gửi ảnh ở một tin, rồi mới
    nói "làm poster đi" ở tin sau. Chỉ nhìn tin cuối thì ảnh coi như biến mất.

    Lấy lần gần nhất chứ không gộp tất cả: Papa gửi ảnh món A, làm xong, rồi gửi
    ảnh món B — gộp lại thì bài đăng mang ảnh cả hai món.
    """
    for m in reversed(history or []):
        if (m.get("role") or "") != "user":
            continue
        found = attached_image_paths(m.get("content") or "")
        if found:
            return found
    return []


def photo_mode_note(images: list[str], *, da_cat: bool = False) -> str:
    """Câu chỉ đạo chọn chế độ A hay B, viết sẵn cho nhân viên.

    Người dùng phổ thông chỉ gửi ảnh rồi nói muốn gì. Họ không biết "chế độ B",
    không biết đường dẫn, không biết phải cắt nền trước. Nên việc chọn chế độ
    phải do máy quyết theo dữ kiện có thật (có ảnh đính kèm hay không), rồi nói
    thẳng cho nhân viên — không phải một luật mơ hồ trong mô tả kỹ năng để nhân
    viên tự suy.

    `da_cat=True` khi ảnh đã được cắt nền TRƯỚC bởi một node công cụ trong quy
    trình. Lúc đó nhân viên không có (và không cần) công cụ cắt — bảo nó đi cắt
    thì nó sẽ báo thiếu công cụ rồi dừng, dù việc cắt đã xong từ bước trước.
    """
    if not images:
        return (
            "NGUỒN ẢNH: Papa CHƯA gửi ảnh sản phẩm nào trong buổi này.\n"
            "→ Dùng CHẾ ĐỘ A: model vẽ toàn bộ tấm ảnh, kể cả món hàng.\n"
            "- KHÔNG được bịa ra khối ẢNH SẢN PHẨM.\n"
            "- KHÔNG bảo Papa đi cắt ảnh hay hỏi đường dẫn file. Papa muốn có ảnh "
            "thật thì chỉ cần bấm kẹp giấy gửi ảnh vào, bạn tự lo phần còn lại."
        )
    danh_sach = "\n".join(f"  {p}" for p in images)
    if da_cat:
        buoc_mot = (
            "1. Ảnh trên ĐÃ ĐƯỢC CẮT NỀN SẴN ở bước trước — dùng thẳng, đừng đi "
            "cắt lại và đừng đòi công cụ cắt.\n"
        )
        ket = ""
    else:
        buoc_mot = (
            "1. Cắt nền ảnh trên bằng công cụ cắt ảnh, lưu kết quả vào thư mục "
            "data\\assets với đuôi .png. Nếu đường dẫn đã có sẵn đuôi _cut.png thì "
            "nó đã cắt rồi, dùng luôn.\n"
        )
        ket = (
            "\nKhông có công cụ cắt ảnh trong buổi này thì nói thẳng là bạn thiếu "
            "công cụ, đừng vờ như đã cắt."
        )
    return (
        "NGUỒN ẢNH: Papa VỪA GỬI ảnh sản phẩm thật:\n" + danh_sach + "\n"
        "→ Dùng CHẾ ĐỘ B, không hỏi lại, không xin xác nhận.\n"
        "Papa là người dùng bình thường, không rành kỹ thuật. Papa chỉ gửi ảnh và "
        "nói muốn gì; mọi bước kỹ thuật là việc của bạn. TUYỆT ĐỐI không bắt Papa "
        "đưa đường dẫn, đặt tên file, chọn thông số hay nhắc tên chế độ.\n"
        "Tự làm đủ các bước:\n"
        + buoc_mot +
        "2. IMAGE PROMPT tả TOÀN BỘ thiết kế poster kể cả chữ tiếng Việt, nhưng "
        "không vẽ món hàng; chừa đúng vùng sản phẩm của template vì ảnh thật sẽ dán vào đó.\n"
        "3. Kèm khối ẢNH SẢN PHẨM trỏ tới file .png đã cắt.\n"
        "4. Kèm khối TEMPLATE. Chỉ xuất POSTER nếu chủ ý dùng đường Pillow dự phòng."
        + ket
    )


# Khoảng an toàn để kẹp số do model sinh ra — xem extract_product_placement.
_SCALE_RANGE = (0.30, 0.90)
_OFFSET_RANGE = (-0.15, 0.15)


def extract_product_placement(llm_output: str) -> tuple[float, float] | None:
    """Kích thước và vị trí sản phẩm trên nền, nếu nhân viên muốn tự quyết.

    Khối tuỳ chọn, đứng sau ẢNH SẢN PHẨM:

        VỊ TRÍ SẢN PHẨM
        cao: 0.72
        xuống: 0.02

    `cao`   — chiều cao sản phẩm / chiều cao nền.
    `xuống` — đẩy xuống dưới tâm bao nhiêu phần chiều cao nền (số âm là đẩy lên).

    Trả None nếu không khai báo, để `compose_on_background` dùng mặc định của nó.

    Kẹp vào khoảng an toàn thay vì tin số nhân viên đưa: đây là số do model sinh
    ra, `cao: 3` hay `xuống: 0.9` là đẩy món hàng ra ngoài khung, ảnh hỏng mà
    không ai biết vì sao. Kẹp thì tệ nhất cũng chỉ là bố cục hơi lệch ý.
    """
    if not re.search(r"VỊ TRÍ SẢN PHẨM|VI TRI SAN PHAM|PRODUCT PLACEMENT",
                     llm_output or "", re.IGNORECASE):
        return None

    def _so(*ten: str) -> float | None:
        for t in ten:
            m = re.search(rf"{t}\s*[:=]\s*(-?[\d.]+)\s*(%?)", llm_output, re.IGNORECASE)
            if m:
                try:
                    v = float(m.group(1))
                except ValueError:
                    continue
                return v / 100 if m.group(2) else v
        return None

    from core.image_compose import default_placement
    mac_dinh_cao, mac_dinh_xuong = default_placement()
    cao = _so("cao", "height", "scale") or mac_dinh_cao
    xuong = _so("xuống", "xuong", "offset")
    xuong = mac_dinh_xuong if xuong is None else xuong
    return (
        min(max(cao, _SCALE_RANGE[0]), _SCALE_RANGE[1]),
        min(max(xuong, _OFFSET_RANGE[0]), _OFFSET_RANGE[1]),
    )


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


def extract_poster(llm_output: str) -> dict | None:
    """Đọc JSON trong khối POSTER và chỉ giữ contract dùng chung của hai skill.

    Dùng ``JSONDecoder.raw_decode`` thay vì regex bắt cặp ngoặc: chuỗi CTA có thể
    chứa dấu ngoặc bình thường. Fence JSON Markdown là tuỳ chọn để Lexapro dễ đọc.
    Khối vắng hoặc JSON lỗi trả None, nhờ đó output cũ đi nguyên đường cũ.
    """

    match = re.search(r"^\s*POSTER\s*:?\s*$", llm_output or "",
                      re.MULTILINE | re.IGNORECASE)
    if not match:
        return None
    raw = (llm_output or "")[match.end():].lstrip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1, flags=re.IGNORECASE)
    try:
        parsed, _ = json.JSONDecoder().raw_decode(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Bỏ qua khối POSTER vì JSON không hợp lệ")
        return None
    from core.poster_layer import normalize_poster
    clean = normalize_poster(parsed)
    return clean or None


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

    # Model chạy qua CLI cố tình để trống base_url (xác thực nằm ở thư mục tài
    # khoản, không có endpoint). Không chặn sớm thì httpx nhận URL tương đối và
    # báo "Request URL is missing an 'http://' or 'https://' protocol" — lỗi đó
    # nói về giao thức chứ không nói ra rằng model này vốn không sinh được ảnh.
    if not (base_url or "").strip():
        raise ImageGenError(
            f"Model '{model}' không có endpoint sinh ảnh. Model chạy qua CLI gói thuê bao "
            "chỉ sinh được chữ — cần một image model riêng để tạo ảnh."
        )

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


def safe_product_path(declared: str | None, data_root: Path) -> Path | None:
    """Kiểm đường dẫn ảnh sản phẩm do NHÂN VIÊN khai báo trước khi dùng.

    Chuỗi này do model sinh ra, không phải dữ liệu tin cậy — chỉ nhận file có
    thật và nằm trong thư mục `data/` của dự án. Không chặn thì một câu khai báo
    trỏ vào file bất kỳ trên máy là đủ để nó đi vào ảnh đăng công khai.
    """
    if not declared:
        return None
    try:
        path = Path(declared.strip()).resolve()
        root = data_root.resolve()
        if not path.is_file() or (root != path and root not in path.parents):
            logger.warning("Bỏ qua ảnh sản phẩm ngoài vùng cho phép: %s", declared)
            return None
        return path
    except Exception:
        logger.exception("Đường dẫn ảnh sản phẩm không đọc được: %s", declared)
        return None


async def generate_with_agent_models(
    *, prompt: str, ratio: tuple[int, int], model_pool_ids: list[int], save_path: Path,
    notify: Callable[[str], Awaitable[None]] | None = None,
    product_overlay: str | Path | None = None,
    placement: tuple[float, float] | None = None,
    poster: Mapping | None = None,
    poster_palette: Mapping | None = None,
    template_code: str | None = None,
    composition_mode: str | None = None,
) -> str | None:
    """Sinh ảnh bằng đúng dàn model đã cấu hình cho nhân viên. Trả None nếu xong,
    hoặc chuỗi lỗi đã diễn giải sẵn cho người đọc nếu thất bại.

    Tách khỏi `api/websocket_workflow._maybe_generate_image` để phòng dạy dùng lại
    được nguyên phần khó: bỏ qua model không vẽ được, thử lần lượt theo thứ tự ưu
    tiên của nhân viên, thử lại một vòng nữa sau 5 giây, và ghi usage. Chép tay
    sang phòng dạy thì hai nơi sẽ lệch nhau — đúng vết xe mà phòng họp từng đi với
    `_build_agent_tools` (xem api/websocket_meeting.py).

    `notify` nhận từng câu thông báo tiến độ; nơi gọi tự quyết định hiển thị ở đâu.
    """
    from core.model_pool_bridge import CLI_API_STYLES, iter_usable_pool_entries
    from hub.database import (
        record_model_usage, record_model_usage_hourly, record_model_call_log,
    )

    async def _say(text: str) -> None:
        if notify:
            await notify(text)

    # TEMPLATE là đường mặc định. POSTER cũ tự chọn fallback để output 2.10.x và
    # các adapter chưa nâng cấp vẫn chạy; nơi gọi cũng có thể ép tường minh bằng
    # composition_mode="template" hoặc "fallback".
    if composition_mode is None:
        resolved_mode = "fallback" if poster else "template"
    else:
        resolved_mode = composition_mode.strip().lower()
        if resolved_mode not in {"template", "fallback"}:
            logger.warning("Chế độ ghép %r không hợp lệ — dùng template", composition_mode)
            resolved_mode = "template"

    from core.poster_templates import get_template
    selected_template = get_template(template_code)

    # Có ảnh sản phẩm thật thì model thiết kế poster (kể cả chữ), rồi dán sản phẩm
    # vào đúng vùng chừa. Nền sinh ở kích thước cuối nên không phải co kéo.
    def _compose_if_needed() -> None:
        if not product_overlay:
            return
        from core.image_compose import compose_on_background
        layout = None
        effective_placement = placement
        if resolved_mode == "fallback" and poster:
            from PIL import Image
            from core.poster_layer import build_poster_layout
            with Image.open(save_path) as background:
                layout = build_poster_layout(
                    background.size, poster, explicit_placement=placement)
            # Không có VỊ TRÍ SẢN PHẨM tường minh thì chính khoảng trống giữa hai
            # khối chữ quyết định cao/xuống. Có khai báo thì build_poster_layout
            # giữ nguyên (sau khi kẹp an toàn), đúng quyền ưu tiên của người dùng.
            effective_placement = (layout.product_scale, layout.product_y_offset)

        if resolved_mode == "template":
            compose_on_background(
                product_overlay, save_path, save_path,
                product_region=selected_template.product_region,
            )
        elif effective_placement:
            scale, y_offset = effective_placement
            compose_on_background(
                product_overlay, save_path, save_path, scale=scale, y_offset=y_offset)
        else:
            compose_on_background(product_overlay, save_path, save_path)

        if layout:
            from PIL import Image
            from core.poster_layer import render_poster_layer
            with Image.open(save_path) as composed:
                rendered = render_poster_layer(composed, layout, palette=poster_palette)
            rendered.save(save_path, "PNG", optimize=True)

    async def _run_image_model(pool_entry: Mapping, image_prompt: str, target: Path,
                               usage_state: dict) -> None:
        """Một lần gọi thật, dùng chung cho lần đầu và lần siết vùng trống."""
        if (pool_entry.get("api_style") or "") == "codex_cli":
            from core.cli_provider import generate_image_via_codex
            await generate_image_via_codex(
                prompt=image_prompt, save_path=target,
                model_id=pool_entry["model_id"],
                codex_home=(pool_entry.get("cli_config_dir") or "").strip() or None,
                ratio=ratio,
            )
        else:
            await generate_image(
                prompt=image_prompt, base_url=pool_entry["base_url"],
                api_key=pool_entry["api_key"], model=pool_entry["model_id"],
                save_path=target, ratio=ratio, usage_state=usage_state,
            )

    async def _record_usage(pool_entry: Mapping, usage_state: dict, model_label: str) -> None:
        for record in (record_model_usage, record_model_usage_hourly, record_model_call_log):
            try:
                await record(pool_entry["id"], usage_state["tokens_in"],
                             usage_state["tokens_out"], usage_state["tokens_cache"])
            except Exception:
                logger.exception("Không ghi được usage cho lần tạo ảnh bằng %s", model_label)

    def _measure_background(path: Path):
        from PIL import Image
        from core.poster_background import measure_empty_product_region
        with Image.open(path) as image:
            return measure_empty_product_region(image, selected_template.product_region)

    def _strict_empty_prompt(original: str) -> str:
        r = selected_template.product_region
        return original.rstrip() + (
            "\n\nCRITICAL RETRY CORRECTION: The rectangular product reservation from "
            f"x={r.left:.0%} to {r.right:.0%} and y={r.top:.0%} to {r.bottom:.0%} "
            "must be genuinely empty background. A real cut-out product photograph will be "
            "pasted over this exact rectangle. Remove every product, prop, character, icon, "
            "badge, card, lettering, strong pattern and decorative object from inside it. "
            "Do not draw a placeholder or silhouette there. Keep all typography and design "
            "elements strictly outside this rectangle. Only a smooth continuous backdrop "
            "and subtle lighting may pass through it."
        )

    ratio_str = f"{ratio[0]}:{ratio[1]}"
    attempt_errors: list[str] = []
    skipped_cli: list[str] = []
    attempted_any = False
    announced = False

    for round_index in range(2):
        failed_label: str | None = None
        async for pool_entry in iter_usable_pool_entries(model_pool_ids or []):
            model_label = f"{pool_entry['name']} · {pool_entry['model_id']}"
            api_style = pool_entry.get("api_style") or ""

            # `claude` CLI không sinh được ảnh, và entry CLI cố tình để trống
            # base_url — không chặn ở đây thì nó văng lỗi thiếu http:// che mất
            # nguyên nhân thật. `codex` CLI thì SINH ĐƯỢC bằng skill imagegen của
            # gói ChatGPT, nên không loại.
            if api_style in CLI_API_STYLES and api_style != "codex_cli":
                if model_label not in skipped_cli:
                    skipped_cli.append(model_label)
                continue

            if not announced:
                await _say(f"⏳ Đang tạo ảnh ({ratio_str})...")
                announced = True
            if failed_label:
                await _say(f"⚠️ {failed_label} lỗi, đang thử {model_label}...")

            attempted_any = True
            usage_state = {"tokens_in": 0, "tokens_out": 0, "tokens_cache": 0}
            try:
                await _run_image_model(pool_entry, prompt, save_path, usage_state)
            except ImageGenError as img_err:
                logger.warning("Tạo ảnh bằng model %s thất bại ở vòng %s: %s",
                               model_label, round_index + 1, img_err)
                attempt_errors.append(f"• {model_label}: {img_err}")
                failed_label = model_label
                continue

            await _record_usage(pool_entry, usage_state, model_label)

            # Chỉ template mới cần vùng rỗng. Fallback vẽ chữ bằng Pillow trên nền
            # trống cũ nên giữ nguyên hành vi 2.10.x và không phát sinh lần gọi model.
            if product_overlay and resolved_mode == "template":
                first_measurement = _measure_background(save_path)
                logger.info(
                    "Đo vùng chừa template %s lần 1: %s",
                    selected_template.code, first_measurement.log_summary(),
                )
                if not first_measurement.empty:
                    await _say("⚠️ Model chưa chừa sạch vùng sản phẩm, đang siết prompt và vẽ lại một lần...")
                    retry_path = save_path.with_name(save_path.stem + "-empty-retry.png")
                    retry_usage = {"tokens_in": 0, "tokens_out": 0, "tokens_cache": 0}
                    try:
                        await _run_image_model(
                            pool_entry, _strict_empty_prompt(prompt), retry_path, retry_usage)
                        await _record_usage(pool_entry, retry_usage, model_label)
                        retry_path.replace(save_path)
                        second_measurement = _measure_background(save_path)
                    except Exception as retry_exc:
                        # Giữ ảnh lần một: retry là lớp bảo vệ chất lượng, không
                        # được biến một lần retry lỗi thành mất luôn poster đã có.
                        logger.warning(
                            "Sinh lại vùng chừa template %s thất bại; vẫn ghép ảnh lần 1: %s; số đo: %s",
                            selected_template.code, retry_exc, first_measurement.log_summary(),
                        )
                    else:
                        logger.info(
                            "Đo vùng chừa template %s lần 2: %s",
                            selected_template.code, second_measurement.log_summary(),
                        )
                        if not second_measurement.empty:
                            logger.warning(
                                "Model vẫn không chừa sạch vùng sản phẩm sau 2 lần; vẫn ghép để có poster. "
                                "template=%s; lần_1={%s}; lần_2={%s}",
                                selected_template.code, first_measurement.log_summary(),
                                second_measurement.log_summary(),
                            )

            if product_overlay:
                await _say("🧩 Đang ghép ảnh sản phẩm lên nền...")
                try:
                    await asyncio.get_running_loop().run_in_executor(None, _compose_if_needed)
                except Exception as exc:
                    # Ghép hỏng thì giữ lại tấm nền vừa vẽ chứ không đánh cả bước
                    # là thất bại — Papa vẫn còn cái để xem và để chê.
                    logger.exception("Ghép ảnh sản phẩm thất bại")
                    await _say(f"⚠️ Vẽ nền xong nhưng ghép sản phẩm hỏng: {exc}")
            return None

        if round_index == 0:
            if not attempted_any:
                if skipped_cli:
                    return (
                        "Nhân viên này chỉ có model không sinh được ảnh ("
                        + ", ".join(skipped_cli)
                        + "). Claude CLI không có khả năng tạo ảnh — hãy gán thêm cho nhân "
                        "viên này một model Codex CLI (dùng skill imagegen của gói ChatGPT, "
                        "không tốn thêm tiền) hoặc một image model qua API."
                    )
                return ("Nhân viên chưa được gán model khả dụng nào. Vui lòng chọn model cho "
                        "nhân viên này ở tab Nhân sự rồi chạy lại.")
            await _say("⚠️ Tất cả model đều lỗi, chờ 5 giây rồi thử lại một vòng...")
            await asyncio.sleep(5)

    err = "Tạo ảnh thất bại sau khi thử hết model của nhân viên:\n" + "\n".join(attempt_errors)
    if skipped_cli:
        err += "\n\n(Đã bỏ qua model không sinh được ảnh: " + ", ".join(skipped_cli) + ")"
    return err
