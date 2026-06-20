from __future__ import annotations

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _list_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://secopsai:secopsai@127.0.0.1:5432/secopsai_edge",
    )
    admin_token: str = os.getenv("SECOPSAI_ADMIN_TOKEN", "dev-admin-token")
    token_secret: str = os.getenv("SECOPSAI_TOKEN_SECRET", "dev-token-secret")
    dashboard_session_ttl_seconds: int = int(
        os.getenv("SECOPSAI_DASHBOARD_SESSION_TTL_SECONDS", "28800")
    )
    auto_create_tables: bool = _bool_env("SECOPSAI_AUTO_CREATE_TABLES", True)
    cors_origins: list[str] = None  # type: ignore[assignment]
    ai_provider: str = os.getenv("AI_PROVIDER", "mock")
    ai_endpoint: str | None = os.getenv("AI_ENDPOINT") or None
    ai_api_key: str | None = os.getenv("AI_API_KEY") or None
    ai_model: str = os.getenv("AI_MODEL", "secopsai-report-v1")
    splunk_hec_enabled: bool = _bool_env("SPLUNK_HEC_ENABLED", False)
    splunk_hec_url: str | None = os.getenv("SPLUNK_HEC_URL") or None
    splunk_hec_token: str | None = os.getenv("SPLUNK_HEC_TOKEN") or None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cors_origins",
            _list_env("SECOPSAI_CORS_ORIGINS", ["http://127.0.0.1:3000", "http://localhost:3000"]),
        )


def get_settings() -> Settings:
    return Settings()
