from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Server ─────────────────────────────────────────────────
    port: int = 3000
    node_env: str = "development"

    # ── Database ────────────────────────────────────────────────
    database_url: str = "postgresql://postgres:password@localhost:5432/hermes_hub"

    # ── Anthropic ───────────────────────────────────────────────
    anthropic_api_key: str = ""
    hermes_model: str = "claude-sonnet-4-6"

    # ── Auth — API key (legacy) ──────────────────────────────────
    hub_api_key: str = ""

    # ── Auth — JWT ──────────────────────────────────────────────
    jwt_secret: str = "change-me"
    jwt_refresh_secret: str = "change-me-refresh"
    jwt_expires_in: str = "15m"           # 15m | 1h | 24h …
    jwt_refresh_expires_in: str = "7d"   # 7d | 30d …

    # Admin bootstrap / workspace
    admin_username: str = ""
    admin_password: str = ""
    admin_email: str = ""
    admin_role: str = "admin"
    workspace_path: str = "/workspace"

    # ── Optional provider keys ──────────────────────────────────
    openai_api_key: str = ""
    elevenlabs_api_key: str = ""

    @property
    def async_database_url(self) -> str:
        """SQLAlchemy async driver URL."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    @property
    def is_dev(self) -> bool:
        return self.node_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
