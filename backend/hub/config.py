"""
Hub Server Configuration – Pydantic Settings
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{(_BACKEND_DIR / 'xanax.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Đường dẫn TUYỆT ĐỐI — đừng đổi lại thành chuỗi ".env". Chuỗi tương đối
        # được phân giải theo thư mục đang đứng, nên chạy từ ngoài backend/ sẽ
        # không thấy file và pydantic lặng lẽ dùng toàn giá trị mặc định: mất
        # HUB_SECRET_KEY, HUB_API_KEY, HUB_LLM_API_BASE... mà không một dòng
        # cảnh báo nào. Hỏng kiểu này chỉ lộ ra khi gọi model thất bại.
        env_file=_BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="HUB_",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    host: str = "localhost"
    port: int = 8000
    debug: bool = True
    title: str = "Xanax Hub Server"
    # NGUỒN DUY NHẤT của số phiên bản. Đừng khai HUB_VERSION trong .env —
    # .env đè lên đây và sửa dòng này sẽ không có tác dụng gì.
    # Quy ước đánh số: xem mục "Đánh số phiên bản" trong README.
    version: str = "2.4.0"
    description: str = "Multi-Agent Orchestration Platform powered by Hermes Agent"

    # Security
    secret_key: str = "change-me-to-a-strong-random-secret"
    api_key: str = "xanax-dev-key-0000"
    cookie_secure: bool | None = None
    # Chỉ bật khi có reverse proxy tin cậy (Caddy/nginx); chạy trần sẽ cho phép giả mạo IP.
    trust_proxy_headers: bool = False
    login_rate_limit_attempts: int = Field(default=8, ge=1)
    login_rate_limit_window_seconds: int = Field(default=900, ge=1)
    login_rate_limit_lock_seconds: int = Field(default=900, ge=1)

    # Các biến XANAX_* cũng được đọc từ backend/.env dù model dùng tiền tố HUB_.
    admin_user: str = Field(default="admin", validation_alias="XANAX_ADMIN_USER")
    admin_pass: str = Field(
        default="xanax",
        validation_alias="XANAX_ADMIN_PASS",
        repr=False,
    )
    no_browser: bool = Field(default=False, validation_alias="XANAX_NO_BROWSER")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Database
    database_url: str = _DEFAULT_DATABASE_URL

    # Hermes Agent (internal framework)
    hermes_max_iterations: int = 10
    hermes_memory_ttl: int = 3600
    hermes_log_level: str = "INFO"

    # Hermes Gateway (NousResearch Hermes CLI API)
    hermes_gateway_url: str = "http://localhost:8642"
    hermes_api_key: str = ""  # API_SERVER_KEY from Hermes .env

    # Xanax Agent Persona
    xanax_name: str = "Xanax"
    xanax_personality: str = "helpful"  # Slug matching Hermes personality or custom

    # Task Queue
    task_queue_max_size: int = 1000
    task_worker_count: int = 4

    # LLM Backend (optional)
    llm_api_base: str = "http://localhost:11434"
    llm_model: str = "hermes3"
    llm_api_key: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return ["*"] if self.debug else []

    @property
    def is_production(self) -> bool:
        return not self.debug

    @property
    def secure_cookie_enabled(self) -> bool:
        """Giá trị cuối cùng cho cờ Secure của cookie phiên."""
        return self.is_production if self.cookie_secure is None else self.cookie_secure

    @property
    def api_docs_enabled(self) -> bool:
        return not self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Global singleton
settings = get_settings()
