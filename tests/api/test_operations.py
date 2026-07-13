from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
from secopsai_api.main import app, settings
from secopsai_api.models import Base


def make_session(revision: str | None) -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)"))
        if revision:
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": revision},
            )
    return sessionmaker(bind=engine)()


def make_client(db: Session) -> TestClient:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_liveness_reports_build_identity_without_database_dependency() -> None:
    response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == settings.release_version
    assert response.json()["commit"]


def test_readiness_requires_exact_schema_head() -> None:
    current_db = make_session(settings.expected_schema_revision)
    stale_db = make_session("0009_organizations")
    current_client = make_client(current_db)
    try:
        current = current_client.get("/readyz")
    finally:
        app.dependency_overrides.clear()
    stale_client = make_client(stale_db)
    try:
        stale = stale_client.get("/readyz")
    finally:
        app.dependency_overrides.clear()

    assert current.status_code == 200
    assert current.json()["status"] == "ready"
    assert stale.status_code == 503
    assert stale.json()["reason"] == "schema_out_of_date"
    assert stale.json()["expected_revision"] == settings.expected_schema_revision


def test_system_status_is_authenticated_and_contains_no_secrets() -> None:
    db = make_session(settings.expected_schema_revision)
    client = make_client(db)
    try:
        denied = client.get("/api/v1/system/status")
        response = client.get(
            "/api/v1/system/status",
            headers={"Authorization": "Bearer dev-admin-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert denied.status_code == 401
    assert response.status_code == 200
    assert response.json()["schema_revision"] == settings.expected_schema_revision
    serialized = response.text.lower()
    assert "admin_token" not in serialized
    assert "token_secret" not in serialized
