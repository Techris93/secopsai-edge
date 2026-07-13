from collections.abc import Generator
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
from secopsai_api.main import app
from secopsai_api.models import (
    Base,
    Organization,
    OrganizationMembership,
    Sensor,
    SensorEnrollment,
    Site,
    User,
    utcnow,
)
from secopsai_api.security import create_dashboard_session, hash_password


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_client(db: Session) -> TestClient:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def seed(db: Session, name: str) -> tuple[Organization, User, Site]:
    organization = Organization(name=name, slug=name.lower())
    user = User(
        email=f"owner-{name.lower()}@example.com",
        password_hash=hash_password("correct-horse-password"),
        role="owner",
    )
    db.add_all([organization, user])
    db.flush()
    db.add(
        OrganizationMembership(
            organization_id=organization.id,
            user_id=user.id,
            role="owner",
            active=True,
        )
    )
    site = Site(organization_id=organization.id, name=f"{name} Office")
    db.add(site)
    db.commit()
    return organization, user, site


def headers(organization: Organization, user: User) -> dict[str, str]:
    token = create_dashboard_session(
        subject=user.email,
        role="owner",
        user_id=user.id,
        session_version=user.session_version,
        organization_id=organization.id,
    )
    return {"Authorization": f"Bearer {token}"}


def test_one_time_enrollment_creates_scoped_sensor_without_leaking_token() -> None:
    db = make_session()
    organization, user, site = seed(db, "Alpha")
    client = make_client(db)
    auth_headers = headers(organization, user)

    try:
        created = client.post(
            "/api/v1/sensor-enrollments",
            headers=auth_headers,
            json={"site_id": site.id, "label": "Reception Pi", "expires_in_minutes": 30},
        )
        token = created.json()["enrollment_token"]
        listed = client.get("/api/v1/sensor-enrollments", headers=auth_headers)
        enrolled = client.post(
            "/api/v1/sensors/enroll",
            json={"enrollment_token": token, "name": "Reception Sensor", "hostname": "pi-edge"},
        )
        reused = client.post(
            "/api/v1/sensors/enroll",
            json={"enrollment_token": token, "name": "Replay Sensor"},
        )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 200
    assert created.json()["state"] == "active"
    assert len(token) >= 32
    assert listed.status_code == 200
    assert "enrollment_token" not in listed.json()[0]
    assert listed.json()[0]["label"] == "Reception Pi"
    assert enrolled.status_code == 200
    assert enrolled.json()["site_id"] == site.id
    assert reused.status_code == 403
    sensor = db.get(Sensor, enrolled.json()["sensor_id"])
    assert sensor is not None and sensor.site_id == site.id
    assert sensor.token_hash != enrolled.json()["sensor_token"]


def test_enrollment_rejects_foreign_site_revocation_and_expiry() -> None:
    db = make_session()
    org_a, user_a, site_a = seed(db, "Alpha")
    _, _, site_b = seed(db, "Bravo")
    client = make_client(db)
    auth_headers = headers(org_a, user_a)

    try:
        foreign = client.post(
            "/api/v1/sensor-enrollments",
            headers=auth_headers,
            json={"site_id": site_b.id, "label": "Foreign"},
        )
        created = client.post(
            "/api/v1/sensor-enrollments",
            headers=auth_headers,
            json={"site_id": site_a.id, "label": "Temporary"},
        )
        enrollment_id = created.json()["id"]
        token = created.json()["enrollment_token"]
        revoked = client.delete(
            f"/api/v1/sensor-enrollments/{enrollment_id}", headers=auth_headers
        )
        rejected = client.post(
            "/api/v1/sensors/enroll",
            json={"enrollment_token": token, "name": "Revoked"},
        )

        expired = SensorEnrollment(
            organization_id=org_a.id,
            site_id=site_a.id,
            label="Expired",
            token_hash="expired-token-hash",
            expires_at=utcnow() - timedelta(minutes=1),
        )
        db.add(expired)
        db.commit()
        expired_response = client.get("/api/v1/sensor-enrollments", headers=auth_headers)
    finally:
        app.dependency_overrides.clear()

    assert foreign.status_code == 404
    assert revoked.status_code == 200
    assert revoked.json()["state"] == "revoked"
    assert rejected.status_code == 403
    states = {row["label"]: row["state"] for row in expired_response.json()}
    assert states["Expired"] == "expired"
