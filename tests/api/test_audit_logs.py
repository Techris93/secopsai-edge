from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
from secopsai_api.main import app
from secopsai_api.models import AuditLog, Base


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def make_client(db: Session) -> TestClient:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_audit_log_endpoint_requires_auth_and_filters_events() -> None:
    db = make_session()
    db.add_all(
        [
            AuditLog(
                action="baseline.saved",
                resource_type="baseline",
                resource_id="baseline-1",
                details={"kind": "asset"},
            ),
            AuditLog(
                action="scan.ingested",
                resource_type="scan",
                resource_id="scan-1",
                details={"assets_seen": 4},
            ),
        ]
    )
    db.commit()
    client = make_client(db)

    try:
        unauthorized = client.get("/api/v1/audit-logs")
        assert unauthorized.status_code == 401

        response = client.get(
            "/api/v1/audit-logs?resource_type=baseline&limit=10",
            headers={"Authorization": "Bearer dev-admin-token"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["action"] == "baseline.saved"
        assert payload[0]["details"] == {"kind": "asset"}
    finally:
        app.dependency_overrides.clear()
