from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from secopsai_api.config import get_settings, normalize_database_url


settings = get_settings()
database_url = normalize_database_url(settings.database_url)
engine_options: dict[str, object] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_timeout": settings.database_pool_timeout_seconds,
}
if database_url.startswith("postgresql+psycopg://"):
    engine_options["connect_args"] = {
        "connect_timeout": settings.database_connect_timeout_seconds,
        "options": f"-c statement_timeout={settings.database_statement_timeout_ms}",
    }

engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
