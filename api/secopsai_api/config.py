from __future__ import annotations

import os
from dataclasses import dataclass

from secopsai_api import __version__


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
    environment: str = os.getenv("SECOPSAI_ENVIRONMENT", "development").strip().lower()
    release_version: str = os.getenv("SECOPSAI_RELEASE_VERSION", __version__)
    release_commit: str = (
        os.getenv("SECOPSAI_RELEASE_COMMIT")
        or os.getenv("RENDER_GIT_COMMIT")
        or "local"
    )
    expected_schema_revision: str = "0011_schema_alignment"
    admin_token: str = os.getenv("SECOPSAI_ADMIN_TOKEN", "dev-admin-token")
    token_secret: str = os.getenv("SECOPSAI_TOKEN_SECRET", "dev-token-secret")
    dashboard_admin_email: str | None = os.getenv("SECOPSAI_DASHBOARD_ADMIN_EMAIL") or None
    dashboard_admin_password: str | None = os.getenv("SECOPSAI_DASHBOARD_ADMIN_PASSWORD") or None
    dashboard_session_ttl_seconds: int = int(
        os.getenv("SECOPSAI_DASHBOARD_SESSION_TTL_SECONDS", "28800")
    )
    login_max_attempts: int = int(os.getenv("SECOPSAI_LOGIN_MAX_ATTEMPTS", "5"))
    login_lockout_seconds: int = int(os.getenv("SECOPSAI_LOGIN_LOCKOUT_SECONDS", "900"))
    auto_create_tables: bool = _bool_env("SECOPSAI_AUTO_CREATE_TABLES", True)
    cors_origins: list[str] = None  # type: ignore[assignment]
    ai_provider: str = os.getenv("AI_PROVIDER", "mock")
    ai_endpoint: str | None = os.getenv("AI_ENDPOINT") or None
    ai_api_key: str | None = os.getenv("AI_API_KEY") or None
    ai_model: str = os.getenv("AI_MODEL", "gpt-5.4-mini")
    ai_max_findings_per_report: int = int(os.getenv("AI_MAX_FINDINGS_PER_REPORT", "50"))
    splunk_hec_enabled: bool = _bool_env("SPLUNK_HEC_ENABLED", False)
    splunk_hec_url: str | None = os.getenv("SPLUNK_HEC_URL") or None
    splunk_hec_token: str | None = os.getenv("SPLUNK_HEC_TOKEN") or None
    smtp_host: str | None = os.getenv("SMTP_HOST") or None
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str | None = os.getenv("SMTP_USERNAME") or None
    smtp_password: str | None = os.getenv("SMTP_PASSWORD") or None
    smtp_from: str = os.getenv("SMTP_FROM", "alerts@secopsai.local")
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN") or None
    webhook_signing_secret: str = os.getenv("SECOPSAI_WEBHOOK_SIGNING_SECRET") or os.getenv(
        "SECOPSAI_TOKEN_SECRET", "dev-token-secret"
    )
    notification_max_attempts: int = int(os.getenv("SECOPSAI_NOTIFICATION_MAX_ATTEMPTS", "4"))
    notification_batch_size: int = int(os.getenv("SECOPSAI_NOTIFICATION_BATCH_SIZE", "50"))

    def __post_init__(self) -> None:
        if self.cors_origins is None:
            object.__setattr__(
                self,
                "cors_origins",
                _list_env("SECOPSAI_CORS_ORIGINS", ["http://127.0.0.1:3000", "http://localhost:3000"]),
            )
        self.validate()

    def validate(self) -> None:
        if self.environment != "production":
            return
        problems: list[str] = []
        if self.admin_token == "dev-admin-token" or len(self.admin_token) < 32:
            problems.append("SECOPSAI_ADMIN_TOKEN must be a random 32+ character value")
        if self.token_secret == "dev-token-secret" or len(self.token_secret) < 32:
            problems.append("SECOPSAI_TOKEN_SECRET must be a random 32+ character value")
        if len(self.webhook_signing_secret) < 32:
            problems.append("SECOPSAI_WEBHOOK_SIGNING_SECRET must contain at least 32 characters")
        if self.auto_create_tables:
            problems.append("SECOPSAI_AUTO_CREATE_TABLES must be false; use Alembic migrations")
        if not self.cors_origins or any(
            origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1")
            for origin in self.cors_origins
        ):
            problems.append("SECOPSAI_CORS_ORIGINS must contain only deployed origins")
        if self.dashboard_admin_password and len(self.dashboard_admin_password) < 16:
            problems.append("SECOPSAI_DASHBOARD_ADMIN_PASSWORD must contain at least 16 characters")
        if problems:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))


def get_settings() -> Settings:
    return Settings()
