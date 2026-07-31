"""Đồng bộ skill loại 'api' (tạo qua giao diện CÔNG CỤ → + Thêm kỹ năng → Dịch vụ
ngoài) thành tool thật trong tool_registry, để agent gọi được ngay — người dùng
không cần sửa code mỗi khi muốn thêm 1 API mới (ví dụ đăng bài Facebook Page)."""
from __future__ import annotations

import json
import logging
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from core.hermes.tool_registry import ToolDefinition, ToolParameter, tool_registry
from core.secret_crypto import decrypt_secret
from core.slugify import slugify

logger = logging.getLogger("xanax.tools.skill_api")

_API_SKILL_PREFIX = "skill_api_"
_RESERVED_CONFIG_KEYS = ("endpoint", "method", "api_key")
_workflow_image_path: ContextVar[str | None] = ContextVar(
    "workflow_image_path", default=None,
)
# Ghi nhận lỗi của các lần gọi API trong 1 bước agent. Trước đây tool trả chuỗi
# lỗi về cho model, model diễn giải lại bằng lời văn rồi bước vẫn tính là "done"
# — dẫn tới quy trình báo đăng bài thành công trong khi Facebook từ chối. Bước
# agent giờ đọc danh sách này để đánh trượt bước khi API thật sự thất bại.
_api_call_failures: ContextVar[list[str] | None] = ContextVar(
    "api_skill_failures", default=None,
)


def begin_api_call_tracking() -> Token:
    return _api_call_failures.set([])


def collect_api_call_failures() -> list[str]:
    return list(_api_call_failures.get() or [])


def end_api_call_tracking(token: Token) -> None:
    _api_call_failures.reset(token)


def _record_api_failure(tool_name: str, detail: str) -> None:
    bucket = _api_call_failures.get()
    if bucket is not None:
        bucket.append(f"{tool_name}: {detail}")


def set_workflow_image_path(image_path: str | None) -> Token:
    """Set the image artifact for tool calls in the current async workflow context."""
    return _workflow_image_path.set(image_path)


def reset_workflow_image_path(token: Token) -> None:
    _workflow_image_path.reset(token)


def tool_name_for_skill(skill: dict) -> str:
    """Tên tool trong registry ứng với 1 skill loại 'api' — dùng chung giữa
    lúc đăng ký (sync_api_skill_tools) và lúc build tool schema cho agent."""
    return _API_SKILL_PREFIX + slugify(skill["name"]).replace("-", "_")


def _is_facebook_page_post_skill(skill: dict, endpoint: str) -> bool:
    """Recognise the existing UI-configured Facebook posting skill."""
    parsed = urlsplit(endpoint)
    return (
        tool_name_for_skill(skill) == "skill_api_facebook_post_page"
        or (
            parsed.hostname in {"graph.facebook.com", "www.graph.facebook.com"}
            and parsed.path.rstrip("/").endswith(("/feed", "/photos"))
        )
    )


def _facebook_photos_endpoint(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    path = parsed.path.rstrip("/")
    if path.endswith("/feed"):
        path = path[:-5] + "/photos"
    elif not path.endswith("/photos"):
        path += "/photos"
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))


def _safe_workflow_image(image_path: str) -> Path:
    from core.project_storage import PROJECTS_DATA_DIR

    candidate = Path(image_path).resolve()
    try:
        candidate.relative_to(PROJECTS_DATA_DIR.resolve())
    except ValueError as exc:
        raise ValueError("Ảnh phải nằm trong thư mục lưu trữ workflow") from exc
    if not candidate.is_file():
        raise ValueError("Không tìm thấy file ảnh của workflow")
    return candidate


def _response_error_detail(text: str) -> str:
    """Một số API (Facebook Graph) có thể trả HTTP 200 kèm object "error"."""
    try:
        parsed = json.loads(text)
    except Exception:
        return ""
    if isinstance(parsed, dict) and isinstance(parsed.get("error"), dict):
        err = parsed["error"]
        return str(err.get("message") or err)
    return ""


def _make_api_skill_handler(
    endpoint: str, method: str, api_key: str, extra: dict, *,
    facebook_page_post: bool = False, tool_name: str = "api",
):
    method = (method or "GET").upper()
    headers = dict(extra.get("headers") or {})
    if api_key and "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {api_key}"
    timeout = extra.get("timeout", 30)

    async def handler(
        body: dict | None = None, image_path: str | None = None, caption: str | None = None,
    ) -> str:
        payload = body or {}
        if facebook_page_post and not image_path:
            image_path = _workflow_image_path.get()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if facebook_page_post and image_path:
                    image_file = _safe_workflow_image(image_path)
                    upload_data = {
                        "caption": caption or payload.get("caption") or payload.get("message") or "",
                        "access_token": api_key,
                    }
                    content_type = {
                        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
                        ".webp": "image/webp",
                    }.get(image_file.suffix.lower(), "image/png")
                    with image_file.open("rb") as source:
                        response = await client.post(
                            _facebook_photos_endpoint(endpoint),
                            data=upload_data,
                            files={"source": (image_file.name, source, content_type)},
                            headers={k: v for k, v in headers.items() if k.lower() != "authorization"},
                        )
                elif method in ("GET", "DELETE"):
                    response = await client.request(method, endpoint, params=payload, headers=headers)
                else:
                    response = await client.request(method, endpoint, json=payload, headers=headers)
                response.raise_for_status()
                text = response.text
                embedded_error = _response_error_detail(text)
                if embedded_error:
                    _record_api_failure(tool_name, embedded_error)
                    return f"Lỗi từ API: {embedded_error}"
                return text[:2000] if len(text) > 2000 else text
        except httpx.HTTPStatusError as e:
            detail = _response_error_detail(e.response.text) or e.response.text[:300]
            _record_api_failure(tool_name, f"HTTP {e.response.status_code} — {detail}")
            return f"HTTP {e.response.status_code}: {e.response.text[:300]}"
        except Exception as e:
            _record_api_failure(tool_name, str(e))
            return f"Gọi API thất bại: {e}"

    return handler


async def sync_api_skill_tools() -> None:
    """Quét toàn bộ skill loại 'api' đang bật và đăng ký/refresh thành tool
    trong tool_registry. Gọi lại hàm này bất cứ khi nào skill có thể đã đổi
    (khi liệt kê /tools/, trước khi agent chạy, khi node 'Gọi công cụ' chạy)
    để không phụ thuộc thứ tự khởi động hay việc ai đã mở trang nào trước."""
    from hub.database import list_skills

    try:
        skills = await list_skills()
    except Exception:
        logger.exception("Không thể tải danh sách skill để đồng bộ api tool")
        return

    for skill in skills:
        if skill.get("type") != "api" or not skill.get("enabled", 1):
            continue
        try:
            config: dict[str, Any] = json.loads(skill.get("config_json") or "{}")
        except Exception:
            logger.warning("Skill api %s có config_json không hợp lệ; bỏ qua", skill.get("id"))
            continue

        endpoint = (config.get("endpoint") or "").strip()
        if not endpoint:
            continue
        method = config.get("method") or "GET"
        # api_key lưu dạng đã mã hoá (xem core/secret_crypto.py); giá trị cũ chưa
        # mã hoá được trả nguyên văn nên skill đang chạy không bị gián đoạn.
        api_key = decrypt_secret(config.get("api_key") or "")
        extra = {k: v for k, v in config.items() if k not in _RESERVED_CONFIG_KEYS}

        tool_name = tool_name_for_skill(skill)
        facebook_page_post = _is_facebook_page_post_skill(skill, endpoint)
        handler = _make_api_skill_handler(
            endpoint, method, api_key, extra,
            facebook_page_post=facebook_page_post, tool_name=tool_name,
        )
        handler.__name__ = tool_name

        tool_registry.register_tool(ToolDefinition(
            name=tool_name,
            description=(
                f"{skill.get('description') or skill['name']} "
                f"[Kỹ năng API do người dùng cấu hình — {method} {endpoint}]"
            ),
            parameters=[ToolParameter(
                name="body",
                type="object",
                description=(
                    "Dữ liệu gửi kèm request dạng JSON object — dùng làm query "
                    "params với GET/DELETE, JSON body với POST/PUT/PATCH."
                ),
                required=False,
                default={},
            )] + ([
                ToolParameter(
                    name="image_path", type="string",
                    description="Đường dẫn file ảnh workflow được cung cấp trong context. Có ảnh thì bắt buộc truyền tham số này để upload trực tiếp.",
                    required=False,
                ),
                ToolParameter(
                    name="caption", type="string",
                    description="Toàn bộ nội dung chữ của bài đăng Facebook đi kèm ảnh.",
                    required=False,
                ),
            ] if facebook_page_post else []),
            handler=handler,
            is_async=True,
            tags=["skill", "api"],
        ))
