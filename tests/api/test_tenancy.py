from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
from secopsai_api.main import app
from secopsai_api.models import (
    Asset,
    Base,
    Finding,
    Organization,
    OrganizationMembership,
    Site,
    User,
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


def seed_workspace(db: Session, *, name: str, email: str, role: str = "owner") -> tuple[Organization, User, Site, Asset, Finding]:
    organization = Organization(name=name, slug=name.lower().replace(" ", "-"))
    user = User(email=email, password_hash=hash_password("correct-horse-password"), role=role)
    db.add_all([organization, user])
    db.flush()
    membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=user.id,
        role=role,
        active=True,
    )
    site = Site(organization_id=organization.id, name=f"{name} Office")
    db.add_all([membership, site])
    db.flush()
    asset = Asset(site_id=site.id, ip_address="192.168.1.10")
    db.add(asset)
    db.flush()
    finding = Finding(
        site_id=site.id,
        asset_id=asset.id,
        type="new_device",
        severity="medium",
        title=f"{name} finding",
        summary="Workspace-isolated test finding",
        evidence={},
        mitre_attack=[],
    )
    db.add(finding)
    db.commit()
    return organization, user, site, asset, finding


def headers_for(organization: Organization, user: User, role: str = "owner") -> dict[str, str]:
    token = create_dashboard_session(
        subject=user.email,
        role=role,
        user_id=user.id,
        session_version=user.session_version,
        organization_id=organization.id,
    )
    return {"Authorization": f"Bearer {token}"}


def test_workspace_lists_and_details_never_cross_tenant_boundary() -> None:
    db = make_session()
    org_a, user_a, site_a, asset_a, finding_a = seed_workspace(
        db, name="Alpha", email="owner-alpha@example.com"
    )
    _, _, site_b, asset_b, finding_b = seed_workspace(
        db, name="Bravo", email="owner-bravo@example.com"
    )
    client = make_client(db)
    headers = headers_for(org_a, user_a)

    try:
        sites = client.get("/api/v1/sites", headers=headers)
        assets = client.get("/api/v1/assets", headers=headers)
        findings = client.get("/api/v1/findings", headers=headers)
        foreign_site_filter = client.get(f"/api/v1/assets?site_id={site_b.id}", headers=headers)
        foreign_asset = client.get(f"/api/v1/assets/{asset_b.id}", headers=headers)
        foreign_finding = client.get(f"/api/v1/findings/{finding_b.id}", headers=headers)
        own_asset = client.get(f"/api/v1/assets/{asset_a.id}", headers=headers)
        own_finding = client.get(f"/api/v1/findings/{finding_a.id}", headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert [row["id"] for row in sites.json()] == [site_a.id]
    assert [row["id"] for row in assets.json()] == [asset_a.id]
    assert [row["id"] for row in findings.json()] == [finding_a.id]
    assert foreign_site_filter.json() == []
    assert foreign_asset.status_code == 404
    assert foreign_finding.status_code == 404
    assert own_asset.status_code == 200
    assert own_finding.status_code == 200


def test_workspace_writes_and_core_export_are_scoped() -> None:
    db = make_session()
    org_a, user_a, _, asset_a, _ = seed_workspace(
        db, name="Alpha", email="owner-alpha@example.com"
    )
    _, _, site_b, asset_b, finding_b = seed_workspace(
        db, name="Bravo", email="owner-bravo@example.com"
    )
    client = make_client(db)
    headers = headers_for(org_a, user_a)

    try:
        rename_foreign = client.patch(
            f"/api/v1/sites/{site_b.id}", headers=headers, json={"name": "Taken Over"}
        )
        triage_foreign = client.post(
            f"/api/v1/findings/{finding_b.id}/status?status_value=resolved", headers=headers
        )
        baseline_foreign = client.post(
            f"/api/v1/assets/{asset_b.id}/baseline",
            headers=headers,
            json={"reason": "foreign"},
        )
        bundle = client.get("/api/v1/core/export", headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert rename_foreign.status_code == 404
    assert triage_foreign.status_code == 404
    assert baseline_foreign.status_code == 404
    assert bundle.status_code == 200
    node_ids = {node["id"] for node in bundle.json()["graph"]["nodes"]}
    assert f"edge:asset:{asset_a.id}" in node_ids
    assert f"edge:asset:{asset_b.id}" not in node_ids
    assert bundle.json()["source_instance"]["organization_id"] == org_a.id


def test_user_can_switch_only_to_an_active_membership() -> None:
    db = make_session()
    org_a, user, _, _, _ = seed_workspace(db, name="Alpha", email="owner@example.com")
    org_b = Organization(name="Bravo", slug="bravo")
    org_c = Organization(name="Charlie", slug="charlie")
    db.add_all([org_b, org_c])
    db.flush()
    db.add(
        OrganizationMembership(
            organization_id=org_b.id,
            user_id=user.id,
            role="viewer",
            active=True,
        )
    )
    db.commit()
    client = make_client(db)
    headers = headers_for(org_a, user)

    try:
        switched = client.post(
            "/api/v1/auth/workspace",
            headers=headers,
            json={"organization_id": org_b.id},
        )
        denied = client.post(
            "/api/v1/auth/workspace",
            headers=headers,
            json={"organization_id": org_c.id},
        )
        switched_headers = {"Authorization": f"Bearer {switched.json()['access_token']}"}
        me = client.get("/api/v1/auth/me", headers=switched_headers)
        forbidden_write = client.post(
            "/api/v1/sites", headers=switched_headers, json={"name": "Viewer Site"}
        )
    finally:
        app.dependency_overrides.clear()

    assert switched.status_code == 200
    assert denied.status_code == 404
    assert me.json()["organization_id"] == org_b.id
    assert me.json()["role"] == "viewer"
    assert forbidden_write.status_code == 403
