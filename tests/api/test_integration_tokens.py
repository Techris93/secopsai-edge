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
    Base,
    IntegrationToken,
    Organization,
    OrganizationMembership,
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
    assert secret.startswith("secopsai_core_")
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
