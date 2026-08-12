"""Mã hoá secret của skill (api_key, token) trước khi ghi vào xanax.db.

Vì sao cần: token Page của Facebook nằm trong bảng `skills` dạng plaintext thì
bất kỳ ai chép được file `xanax.db` — hoặc một bản backup của nó — đều dùng được
token đó để đăng bài lên fanpage. Mã hoá ở đây chặn đúng đường đó.

Nói rõ giới hạn để không ngộ nhận: đây KHÔNG phải lớp bảo vệ chống truy cập API.
Nếu `/api/*` vẫn không có xác thực thì người lạ vẫn gọi được endpoint và server
vẫn giải mã ra để dùng. Mã hoá bảo vệ dữ liệu KHI NGHỈ (file .db, backup, đồng bộ
cloud), không bảo vệ dữ liệu khi đang phục vụ.

Định dạng lưu: "enc:v1:<base64(nonce||ciphertext)>" — có tiền tố nên phân biệt
được với giá trị plaintext cũ, cho phép chuyển đổi dần mà không vỡ dữ liệu đang có.
"""
from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger("xanax.secret_crypto")

_PREFIX = "enc:v1:"
_NONCE_LEN = 12  # khuyến nghị của AES-GCM
_KEY_ENV = "XANAX_SECRET_KEY"
_KEY_FILE = Path(__file__).parent.parent / "data" / ".secret_key"
_ENV_FILE = Path(__file__).parent.parent / ".env"

_key_cache: bytes | None = None


def _key_from_env_file() -> str:
    """XANAX_SECRET_KEY ghi trong backend/.env.

    Đọc riêng ở đây chứ không dựa vào hub/config.py: Settings có env_prefix="HUB_"
    nên nó chỉ nạp các khoá HUB_*, và pydantic-settings không đổ giá trị vào
    os.environ. Trước đây khoá này ghi trong .env mà KHÔNG có tác dụng gì — hệ
    thống vẫn chạy nhờ file .secret_key, nên không ai phát hiện ra.
    """
    if not _ENV_FILE.exists():
        return ""
    try:
        from dotenv import dotenv_values
        return (dotenv_values(_ENV_FILE).get(_KEY_ENV) or "").strip()
    except Exception:
        logger.exception("Không đọc được %s để lấy %s", _ENV_FILE, _KEY_ENV)
        return ""


def _load_key() -> bytes:
    """Khoá 32 byte. Thứ tự ưu tiên: biến môi trường → backend/.env → file
    data/.secret_key → tự sinh mới.

    Sinh tự động là chủ ý: nếu bắt buộc phải cấu hình mới chạy được thì mọi
    người sẽ tắt mã hoá đi cho nhanh. Khi deploy thật thì đặt XANAX_SECRET_KEY
    để khoá không nằm cùng chỗ với file .db mà nó bảo vệ.

    CẢNH BÁO khi đổi khoá: mọi secret đã lưu đều mã hoá bằng khoá CŨ. Đặt một
    khoá khác với khoá đang dùng là không giải mã lại được, không có đường khôi
    phục — phải nhập tay lại toàn bộ api_key/token của skill.
    """
    global _key_cache
    if _key_cache is not None:
        return _key_cache

    raw = (os.environ.get(_KEY_ENV) or "").strip() or _key_from_env_file()
    if raw:
        try:
            key = base64.urlsafe_b64decode(raw)
            if len(key) != 32:
                raise ValueError(f"khoá phải 32 byte sau khi giải base64, đang là {len(key)}")
            _key_cache = key
            return key
        except Exception as exc:
            raise RuntimeError(
                f"{_KEY_ENV} không hợp lệ ({exc}). Tạo khoá mới bằng: "
                "python -c \"import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())\""
            ) from exc

    if _KEY_FILE.exists():
        key = base64.urlsafe_b64decode(_KEY_FILE.read_text(encoding="utf-8").strip())
    else:
        key = os.urandom(32)
        _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _KEY_FILE.write_text(base64.urlsafe_b64encode(key).decode(), encoding="utf-8")
        try:
            os.chmod(_KEY_FILE, 0o600)  # không có tác dụng thật trên Windows, vô hại
        except OSError:
            pass
        logger.warning(
            "Chưa có %s — đã sinh khoá mới tại %s. Khoá nằm CẠNH file .db nên chỉ "
            "chống được việc chép riêng file .db. Khi deploy hãy đặt %s.",
            _KEY_ENV, _KEY_FILE, _KEY_ENV,
        )
    _key_cache = key
    return key


# Các khoá trong config_json của skill được coi là secret. "api_key" dùng cho
# skill loại api, "token" cho loại mcp.
SECRET_CONFIG_KEYS = ("api_key", "token")

# Giá trị trả về thay cho secret thật. Khi form gửi lại đúng chuỗi này nghĩa là
# người dùng KHÔNG sửa ô đó — giữ nguyên giá trị đã lưu, xem merge_secret_config.
MASK = "••••••••"


def is_encrypted(value: str | None) -> bool:
    return bool(value) and str(value).startswith(_PREFIX)


def encrypt_secret(plaintext: str | None) -> str:
    """Mã hoá. Chuỗi rỗng giữ nguyên rỗng; giá trị đã mã hoá thì không mã hoá chồng."""
    text = str(plaintext or "")
    if not text or is_encrypted(text):
        return text
    nonce = os.urandom(_NONCE_LEN)
    blob = nonce + AESGCM(_load_key()).encrypt(nonce, text.encode("utf-8"), None)
    return _PREFIX + base64.urlsafe_b64encode(blob).decode()


def decrypt_secret(value: str | None) -> str:
    """Giải mã. Giá trị KHÔNG có tiền tố được trả nguyên văn — đó là secret cũ
    lưu trước khi có mã hoá, vẫn phải dùng được cho tới khi migrate xong."""
    text = str(value or "")
    if not is_encrypted(text):
        return text
    try:
        blob = base64.urlsafe_b64decode(text[len(_PREFIX):])
        return AESGCM(_load_key()).decrypt(blob[:_NONCE_LEN], blob[_NONCE_LEN:], None).decode("utf-8")
    except Exception:
        # Sai khoá (vd đổi XANAX_SECRET_KEY mà không migrate) — không làm sập cả
        # luồng gọi tool, trả rỗng để tầng trên báo lỗi xác thực rõ ràng hơn.
        logger.error("Không giải mã được secret — kiểm tra %s có đúng khoá đã dùng để mã hoá không", _KEY_ENV)
        return ""


# ── Helper cho config_json của skill ────────────────────────────────────────

def encrypt_secret_config(config: dict) -> dict:
    """Mã hoá các khoá secret trong config trước khi ghi DB."""
    out = dict(config or {})
    for key in SECRET_CONFIG_KEYS:
        if out.get(key):
            out[key] = encrypt_secret(out[key])
    return out


def mask_secret_config(config: dict) -> dict:
    """Thay secret bằng MASK trước khi trả ra API. Ô rỗng vẫn để rỗng để giao
    diện phân biệt được 'chưa đặt' với 'đã đặt nhưng đang ẩn'."""
    out = dict(config or {})
    for key in SECRET_CONFIG_KEYS:
        if out.get(key):
            out[key] = MASK
    return out


def merge_secret_config(new_config: dict, old_config: dict | None) -> dict:
    """Ghép config mới từ form với config đã lưu.

    Form nhận về MASK thay cho secret thật, nên nếu người dùng không sửa ô đó thì
    giá trị gửi lên chính là MASK — phải giữ lại giá trị cũ, nếu không mỗi lần bấm
    Lưu (kể cả chỉ sửa mô tả) sẽ ghi đè token thật bằng chuỗi dấu chấm.
    """
    out = dict(new_config or {})
    old = old_config or {}
    for key in SECRET_CONFIG_KEYS:
        if out.get(key) == MASK:
            if old.get(key):
                out[key] = old[key]      # đã mã hoá sẵn trong DB, giữ nguyên
            else:
                out.pop(key, None)
    return out
