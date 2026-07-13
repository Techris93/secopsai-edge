from dataclasses import replace

import pytest

from secopsai_api.config import Settings, normalize_database_url


def test_normalize_database_url_uses_psycopg_driver_for_render_urls() -> None:
    assert (
        normalize_database_url("postgresql://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )
    assert (
        normalize_database_url("postgres://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )


def test_normalize_database_url_leaves_explicit_driver_urls_unchanged() -> None:
    assert (
        normalize_database_url("postgresql+psycopg://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )
    assert normalize_database_url("sqlite+pysqlite:///:memory:") == "sqlite+pysqlite:///:memory:"


def test_production_configuration_rejects_development_secrets_and_origins() -> None:
    with pytest.raises(RuntimeError, match="Unsafe production configuration"):
        replace(Settings(), environment="production")


def test_mfa_encryption_key_has_an_independent_rotation_boundary() -> None:
    settings = Settings()

    assert settings.mfa_encryption_key != settings.token_secret


def test_production_configuration_accepts_explicit_hardened_values() -> None:
    hardened = replace(
        Settings(),
        environment="production",
        admin_token="a" * 48,
        token_secret="b" * 48,
        mfa_encryption_key="d" * 48,
        webhook_signing_secret="c" * 48,
        auto_create_tables=False,
        cors_origins=["https://edge.secopsai.dev"],
        dashboard_admin_password="correct-horse-password",
    )

    hardened.validate()


def test_production_smtp_requires_a_secure_reset_url() -> None:
    base = replace(
        Settings(),
        environment="production",
        admin_token="a" * 48,
        token_secret="b" * 48,
        mfa_encryption_key="d" * 48,
        webhook_signing_secret="c" * 48,
        auto_create_tables=False,
        cors_origins=["https://edge.secopsai.dev"],
    )
    with pytest.raises(RuntimeError, match="DASHBOARD_RESET_URL is required"):
        replace(base, smtp_host="smtp.example.test", dashboard_reset_url=None)
    with pytest.raises(RuntimeError, match="must be an HTTPS URL"):
        replace(
            base,
            smtp_host="smtp.example.test",
            dashboard_reset_url="http://edge.secopsai.dev/settings",
        )

    replace(
        base,
        smtp_host="smtp.example.test",
        dashboard_reset_url="https://edge.secopsai.dev/settings",
    ).validate()


def test_pilot_configuration_uses_the_same_secret_guardrails_as_production() -> None:
    with pytest.raises(RuntimeError, match="Unsafe production configuration"):
        replace(Settings(), environment="pilot")


def test_ai_report_guardrails_reject_unbounded_or_invalid_values() -> None:
    with pytest.raises(RuntimeError, match="AI_MAX_FINDINGS_PER_REPORT"):
        replace(Settings(), ai_max_findings_per_report=0)
    with pytest.raises(RuntimeError, match="AI_REPORT_COOLDOWN_SECONDS"):
        replace(Settings(), ai_report_cooldown_seconds=-1)
    with pytest.raises(RuntimeError, match="AI_REPORT_COOLDOWN_SECONDS"):
        replace(Settings(), ai_report_cooldown_seconds=86_401)


def test_ai_report_cooldown_can_be_disabled_for_controlled_tests() -> None:
    settings = replace(Settings(), ai_report_cooldown_seconds=0)

    assert settings.ai_report_cooldown_seconds == 0
