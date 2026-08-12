"""
Hub Server Configuration – Pydantic Settings
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{(_BACKEND_DIR / 'xanax.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
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
    version: str = "0.1.0"
    description: str = "Multi-Agent Orchestration Platform powered by Hermes Agent"

    # Security
    secret_key: str = "change-me-to-a-strong-random-secret"
    api_key: str = "xanax-dev-key-0000"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Global singleton
settings = get_settings()
