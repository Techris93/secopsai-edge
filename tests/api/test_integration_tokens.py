from collections.abc import Generator
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
from secopsai_api.main import app
from secopsai_api.models import (
    Asset,
    AuditLog,
    Base,
    IntegrationToken,
    Organization,
    OrganizationMembership,
    ScanJob,
    Sensor,
    Site,
    User,
    utcnow,
)
from secopsai_api.security import create_dashboard_session, hash_password, hash_secret


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


def seed(db: Session, name: str) -> tuple[Organization, User, Site, Asset]:
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
    db.flush()
    asset = Asset(site_id=site.id, ip_address="192.168.1.10")
    db.add(asset)
    db.commit()
    return organization, user, site, asset


def headers(organization: Organization, user: User, role: str = "owner") -> dict[str, str]:
    token = create_dashboard_session(
        subject=user.email,
        role=role,
        user_id=user.id,
        session_version=user.session_version,
        organization_id=organization.id,
    )
    return {"Authorization": f"Bearer {token}"}


def test_core_export_token_is_one_time_visible_scoped_and_revocable() -> None:
    db = make_session()
    org_a, user_a, _, asset_a = seed(db, "Alpha")
    _, _, _, asset_b = seed(db, "Bravo")
    client = make_client(db)
    owner_headers = headers(org_a, user_a)

    try:
        created = client.post(
            "/api/v1/integration-tokens",
            headers=owner_headers,
            json={"name": "Core sync", "scopes": ["core:export"], "expires_in_days": 30},
        )
        secret = created.json()["access_token"]
        listed = client.get("/api/v1/integration-tokens", headers=owner_headers)
        token_headers = {"Authorization": f"Bearer {secret}"}
        exported = client.get("/api/v1/core/export", headers=token_headers)
        denied_elsewhere = client.get("/api/v1/assets", headers=token_headers)
        revoked = client.delete(
            f"/api/v1/integration-tokens/{created.json()['id']}", headers=owner_headers
        )
        denied_after_revoke = client.get("/api/v1/core/export", headers=token_headers)
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 200
    assert secret.startswith("secopsai_integration_")
    assert "access_token" not in listed.json()[0]
    stored = db.get(IntegrationToken, created.json()["id"])
    assert stored is not None
    assert stored.token_hash != secret
    assert stored.last_used_at is not None
    assert exported.status_code == 200
    node_ids = {node["id"] for node in exported.json()["graph"]["nodes"]}
    assert f"edge:asset:{asset_a.id}" in node_ids
    assert f"edge:asset:{asset_b.id}" not in node_ids
    assert exported.json()["source_instance"]["organization_id"] == org_a.id
    assert denied_elsewhere.status_code == 403
    assert revoked.json()["state"] == "revoked"
    assert denied_after_revoke.status_code == 403


def test_legacy_core_token_prefix_remains_accepted() -> None:
    db = make_session()
    organization, _, _, _ = seed(db, "Alpha")
    legacy_secret = "secopsai_core_existing-deployed-token"
    db.add(
        IntegrationToken(
            organization_id=organization.id,
            name="Existing Core sync",
            token_hash=hash_secret(legacy_secret),
            scopes=["core:export"],
            expires_at=utcnow() + timedelta(days=30),
        )
    )
    db.commit()
    client = make_client(db)

    try:
        response = client.get(
            "/api/v1/core/export",
            headers={"Authorization": f"Bearer {legacy_secret}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


def test_integration_token_rejects_bad_scope_expiry_and_foreign_revocation() -> None:
    db = make_session()
    org_a, user_a, _, _ = seed(db, "Alpha")
    org_b, user_b, _, _ = seed(db, "Bravo")
    client = make_client(db)
    headers_a = headers(org_a, user_a)
    headers_b = headers(org_b, user_b)

    try:
        bad_scope = client.post(
            "/api/v1/integration-tokens",
            headers=headers_a,
            json={"name": "Too broad", "scopes": ["admin:*"], "expires_in_days": 30},
        )
        created = client.post(
            "/api/v1/integration-tokens",
            headers=headers_a,
            json={"name": "Expires", "expires_in_days": 30},
        )
        token_id = created.json()["id"]
        secret = created.json()["access_token"]
        stored = db.get(IntegrationToken, token_id)
        assert stored is not None
        stored.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        expired = client.get(
            "/api/v1/core/export", headers={"Authorization": f"Bearer {secret}"}
        )
        foreign_revoke = client.delete(
            f"/api/v1/integration-tokens/{token_id}", headers=headers_b
        )
    finally:
        app.dependency_overrides.clear()

    assert bad_scope.status_code == 400
    assert expired.status_code == 403
    assert foreign_revoke.status_code == 404


def test_operations_read_token_is_workspace_scoped_and_read_only() -> None:
    db = make_session()
    org_a, user_a, site_a, _ = seed(db, "Alpha")
    _, _, site_b, _ = seed(db, "Bravo")
    client = make_client(db)
    owner_headers = headers(org_a, user_a)
    sensor = Sensor(
        site_id=site_a.id,
        name="Alpha Sensor",
        hostname="alpha-sensor",
        token_hash="unused-test-hash",
    )
    db.add(sensor)
    db.flush()
    stale_job = ScanJob(
        site_id=site_a.id,
        sensor_id=sensor.id,
        target_cidr="192.168.1.0/24",
        status="running",
        updated_at=utcnow() - timedelta(minutes=30),
    )
    db.add(stale_job)
    db.commit()

    try:
        created = client.post(
            "/api/v1/integration-tokens",
            headers=owner_headers,
            json={"name": "Operator dashboard", "scopes": ["operations:read"], "expires_in_days": 30},
        )
        secret = created.json()["access_token"]
        token_headers = {"Authorization": f"Bearer {secret}"}
        sites = client.get("/api/v1/sites", headers=token_headers)
        sensors = client.get("/api/v1/sensors", headers=token_headers)
        schedules = client.get("/api/v1/scan-schedules", headers=token_headers)
        jobs = client.get("/api/v1/scan-jobs", headers=token_headers)
        core_export = client.get("/api/v1/core/export", headers=token_headers)
        assets = client.get("/api/v1/assets", headers=token_headers)
        mutation = client.post(
            "/api/v1/sites",
            headers=token_headers,
            json={"name": "Must not be created"},
        )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 200
    assert {item["id"] for item in sites.json()} == {site_a.id}
    assert site_b.id not in {item["id"] for item in sites.json()}
    assert sensors.status_code == 200
    assert schedules.status_code == 200
    assert jobs.status_code == 200
    assert core_export.status_code == 403
    assert assets.status_code == 403
    assert mutation.status_code == 403
    db.refresh(stale_job)
    assert stale_job.status == "running"


def test_integration_token_can_inspect_only_its_own_lifecycle() -> None:
    db = make_session()
    organization, user, _, _ = seed(db, "Alpha")
    client = make_client(db)
    owner_headers = headers(organization, user)

    try:
        created = client.post(
            "/api/v1/integration-tokens",
            headers=owner_headers,
            json={"name": "Operator dashboard", "scopes": ["operations:read"], "expires_in_days": 7},
        )
        secret = created.json()["access_token"]
        inspected = client.get(
            "/api/v1/integration-tokens/self",
            headers={"Authorization": f"Bearer {secret}"},
        )
        denied_admin = client.get("/api/v1/integration-tokens/self", headers=owner_headers)
    finally:
        app.dependency_overrides.clear()

    assert inspected.status_code == 200
    assert inspected.json()["id"] == created.json()["id"]
    assert inspected.json()["scopes"] == ["operations:read"]
    assert inspected.json()["expires_in_days"] == 7
    assert inspected.json()["rotation_recommended"] is True
    assert "access_token" not in inspected.json()
    assert denied_admin.status_code == 403


def test_rotation_creates_overlap_and_preserves_previous_token_until_revoked() -> None:
    db = make_session()
    organization, user, _, _ = seed(db, "Alpha")
    client = make_client(db)
    owner_headers = headers(organization, user)

    try:
        created = client.post(
            "/api/v1/integration-tokens",
            headers=owner_headers,
            json={"name": "Core sync", "scopes": ["core:export"], "expires_in_days": 30},
        )
        previous_secret = created.json()["access_token"]
        rotated = client.post(
            f"/api/v1/integration-tokens/{created.json()['id']}/rotate",
            headers=owner_headers,
            json={"expires_in_days": 90},
        )
        replacement_secret = rotated.json()["access_token"]
        previous_access = client.get(
            "/api/v1/core/export",
            headers={"Authorization": f"Bearer {previous_secret}"},
        )
        replacement_access = client.get(
            "/api/v1/core/export",
            headers={"Authorization": f"Bearer {replacement_secret}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert rotated.status_code == 200
    assert rotated.json()["id"] != created.json()["id"]
    assert rotated.json()["name"] == "Core sync"
    assert rotated.json()["scopes"] == ["core:export"]
    assert rotated.json()["expires_in_days"] == 90
    assert previous_secret != replacement_secret
    assert previous_access.status_code == 200
    assert replacement_access.status_code == 200
    previous = db.get(IntegrationToken, created.json()["id"])
    replacement = db.get(IntegrationToken, rotated.json()["id"])
    assert previous is not None and previous.revoked_at is None
    assert replacement is not None and replacement.token_hash != replacement_secret
    audit = db.query(AuditLog).filter(AuditLog.action == "integration_token.rotated").one()
    assert audit.resource_id == previous.id
    assert audit.details["replacement_id"] == replacement.id
    assert audit.details["previous_remains_active"] is True


def test_revoked_or_foreign_integration_token_cannot_be_rotated() -> None:
    db = make_session()
    org_a, user_a, _, _ = seed(db, "Alpha")
    org_b, user_b, _, _ = seed(db, "Bravo")
    client = make_client(db)
    headers_a = headers(org_a, user_a)
    headers_b = headers(org_b, user_b)

    try:
        created = client.post(
            "/api/v1/integration-tokens",
            headers=headers_a,
            json={"name": "Core sync", "scopes": ["core:export"], "expires_in_days": 30},
        )
        token_id = created.json()["id"]
        foreign = client.post(
            f"/api/v1/integration-tokens/{token_id}/rotate",
            headers=headers_b,
            json={"expires_in_days": 90},
        )
        client.delete(f"/api/v1/integration-tokens/{token_id}", headers=headers_a)
        revoked = client.post(
            f"/api/v1/integration-tokens/{token_id}/rotate",
            headers=headers_a,
            json={"expires_in_days": 90},
        )
    finally:
        app.dependency_overrides.clear()

    assert foreign.status_code == 404
    assert revoked.status_code == 409


def test_viewer_cannot_manage_integration_tokens() -> None:
    db = make_session()
    organization, _, _, _ = seed(db, "Alpha")
    viewer = User(
        email="viewer-alpha@example.com",
        password_hash=hash_password("correct-horse-password"),
        role="viewer",
    )
    db.add(viewer)
    db.flush()
    db.add(
        OrganizationMembership(
            organization_id=organization.id,
            user_id=viewer.id,
            role="viewer",
            active=True,
        )
    )
    db.commit()
    client = make_client(db)
    viewer_headers = headers(organization, viewer, role="viewer")

    try:
        listed = client.get("/api/v1/integration-tokens", headers=viewer_headers)
        created = client.post(
            "/api/v1/integration-tokens",
            headers=viewer_headers,
            json={"name": "Forbidden", "expires_in_days": 30},
        )
    finally:
        app.dependency_overrides.clear()

    assert listed.status_code == 403
    assert created.status_code == 403
