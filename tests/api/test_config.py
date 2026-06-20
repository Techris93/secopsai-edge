from secopsai_api.config import normalize_database_url


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
