"""Gác xác thực cho toàn bộ /api/* và /ws/*.

Trước đây chỉ các trang HTML kiểm tra phiên đăng nhập (xem _is_authenticated trong
hub/server.py); các router API được gắn thẳng, không có Depends nào. Kết quả đo
được: 9/10 endpoint nhạy cảm trả 200 khi gọi không kèm cookie, và POST /api/skills/
tạo được bản ghi mới — tức người lạ đọc VÀ sửa được cấu hình nhân viên, quy trình,
skill.

Chọn middleware thay vì thêm Depends vào từng router là có chủ ý: middleware mặc
định ĐÓNG, route mới thêm sau này tự động được bảo vệ. Kiểu Depends thì mỗi router
mới là một cơ hội quên, mà quên thì không có gì báo.

Dùng ASGI middleware thuần (không phải @app.middleware("http")) vì cái sau CHỈ chạy
với scope http — WebSocket sẽ lọt lưới, mà /ws/meeting chính là nơi chứa nội dung
họp và điều khiển quy trình.
"""
from __future__ import annotations

import json
import logging
from http.cookies import SimpleCookie

from hub.config import settings
from hub.database import COOKIE_NAME, validate_session

logger = logging.getLogger("xanax.auth_guard")

# Đường phải mở, kèm lý do — đừng thêm vào đây nếu không có lý do tương đương.
_PUBLIC_EXACT = {
    "/api/auth/login",      # chưa đăng nhập thì mới gọi cái này
    "/api/auth/logout",     # phiên hỏng vẫn phải thoát được
    "/api/auth/me",         # tự trả 401 đúng ngữ nghĩa cho giao diện dò trạng thái
    "/api/health",          # probe của reverse proxy / uptime monitor
    "/api/health/ready",
}

# Webhook trigger từ n8n/Zapier/curl: token trong URL đã là bí mật riêng của từng
# workflow (xem _ensure_webhook_token trong api/routes/workflow.py), bên gọi không
# có cookie phiên.
_PUBLIC_PREFIXES = ("/api/workflow/hooks/",)

_GUARDED_PREFIXES = ("/api/", "/ws/")

# Giá trị mẫu trong .env.example. Nếu HUB_API_KEY vẫn là chuỗi này thì KHÔNG chấp
# nhận xác thực bằng header — bật lên sẽ thành cửa sau ai cũng đoán được.
_DEFAULT_API_KEY = "xanax-dev-key-0000"


def _is_guarded(path: str) -> bool:
    if not path.startswith(_GUARDED_PREFIXES):
        return False
    if path in _PUBLIC_EXACT:
        return False
    return not path.startswith(_PUBLIC_PREFIXES)


def _header(scope, name: bytes) -> str:
    for key, value in scope.get("headers") or []:
        if key == name:
            return value.decode("latin-1")
    return ""


def _session_token(scope) -> str:
    raw = _header(scope, b"cookie")
    if not raw:
        return ""
    try:
        return SimpleCookie(raw).get(COOKIE_NAME).value  # type: ignore[union-attr]
    except Exception:
        return ""


def _api_key_ok(scope) -> bool:
    """Cho phép gọi bằng X-API-Key để tự động hoá (cron, script) không cần phiên."""
    configured = (settings.api_key or "").strip()
    if not configured or configured == _DEFAULT_API_KEY:
        return False
    return _header(scope, b"x-api-key") == configured


class AuthGuardMiddleware:
    """Chặn mọi request tới /api/* và /ws/* nếu chưa đăng nhập."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket") or not _is_guarded(scope.get("path", "")):
            await self.app(scope, receive, send)
            return

        if _api_key_ok(scope):
            await self.app(scope, receive, send)
            return

        token = _session_token(scope)
        user = await validate_session(token) if token else None
        if user:
            scope["user"] = user       # route nào cần biết ai đang gọi thì đọc ở đây
            await self.app(scope, receive, send)
            return

        logger.info("Chặn truy cập chưa xác thực: %s %s",
                    scope.get("method", scope["type"]), scope.get("path"))
        await self._deny(scope, receive, send)

    async def _deny(self, scope, receive, send) -> None:
        if scope["type"] == "websocket":
            # Phải nhận connect trước rồi mới đóng được, nếu không client nhận lỗi
            # handshake khó hiểu thay vì mã đóng rõ ràng.
            await receive()
            await send({"type": "websocket.close", "code": 1008, "reason": "Chưa đăng nhập"})
            return
        body = json.dumps({"detail": "Chưa đăng nhập hoặc phiên đã hết hạn"}).encode()
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})
