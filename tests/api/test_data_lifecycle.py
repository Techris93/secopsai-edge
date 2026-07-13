from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import secopsai_api.main as main_module
from secopsai_api.database import get_db
from secopsai_api.main import app
from secopsai_api.models import (
    Asset,
    AssetObservation,
    AuditLog,
    Base,
    DataLifecyclePolicy,
    Finding,
    FindingNote,
    NotificationDelivery,
    NotificationEndpoint,
    Organization,
    OrganizationMembership,
    Report,
    ScanJob,
    ScanRun,
    Sensor,
    Service,
    Site,
    User,
    WifiNetwork,
    utcnow,
)
from secopsai_api.security import create_dashboard_session, hash_password


PASSWORD = "correct-horse-password"


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


def seed_workspace(db: Session, suffix: str = "alpha") -> tuple[Organization, User, Site]:
    organization = Organization(name=f"Org {suffix}", slug=f"org-{suffix}")
    user = User(
        email=f"owner-{suffix}@example.com",
        password_hash=hash_password(PASSWORD),
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
    site = Site(organization_id=organization.id, name=f"{suffix.title()} Office")
    db.add(site)
    db.commit()
    return organization, user, site


def headers_for(organization: Organization, user: User) -> dict[str, str]:
    token = create_dashboard_session(
        subject=user.email,
        role="owner",
        user_id=user.id,
        session_version=user.session_version,
        organization_id=organization.id,
    )
    return {"Authorization": f"Bearer {token}"}


def seed_site_data(db: Session, site: Site) -> tuple[Sensor, ScanJob]:
    now = utcnow()
    sensor = Sensor(
        site_id=site.id,
        name="Pilot sensor",
        hostname="pilot.local",
        token_hash="must-never-export",
    )
    db.add(sensor)
    db.flush()
    scan = ScanRun(
        site_id=site.id,
        sensor_id=sensor.id,
        target_cidr="192.168.1.0/24",
        status="completed",
        completed_at=now,
        summary={"assets": 1},
    )
    job = ScanJob(
        site_id=site.id,
        sensor_id=sensor.id,
        target_cidr="192.168.1.0/24",
        status="queued",
    )
    asset = Asset(site_id=site.id, ip_address="192.168.1.10", mac_address="AA:BB:CC:DD:EE:FF")
    wifi = WifiNetwork(
        site_id=site.id,
        sensor_id=sensor.id,
        ssid="Office",
        bssid="11:22:33:44:55:66",
    )
    db.add_all([scan, job, asset, wifi])
    db.flush()
    observation = AssetObservation(
        site_id=site.id,
        sensor_id=sensor.id,
        scan_id=scan.id,
        asset_id=asset.id,
        ip_address=asset.ip_address,
        observed_at=now,
        raw_source="nmap",
        raw={"raw_nmap": "must-never-export"},
    )
    service = Service(asset_id=asset.id, port=22, name="ssh")
    finding = Finding(
        site_id=site.id,
        asset_id=asset.id,
        type="risky_open_port",
        severity="medium",
        title="SSH exposed",
        summary="Review access",
        evidence={"port": 22},
    )
    db.add_all([observation, service, finding])
    db.flush()
    endpoint = NotificationEndpoint(
        organization_id=site.organization_id,
        site_id=site.id,
        name="Pilot webhook",
        type="webhook",
        target="https://hooks.example.test/private-token",
        last_error="Delivery to https://hooks.example.test/private-token failed",
    )
    db.add_all(
        [
            FindingNote(finding_id=finding.id, author="owner", body="Investigating"),
            Report(
                site_id=site.id,
                title="Pilot report",
                summary="Summary",
                risk_level="medium",
                content={"provider": "mock"},
            ),
            endpoint,
            AuditLog(
                organization_id=site.organization_id,
                sensor_id=sensor.id,
                action="scan.completed",
                resource_type="site",
                resource_id=site.id,
                details={"assets": 1, "api_token": "must-never-export"},
            ),
        ]
    )
    db.flush()
    db.add(
        NotificationDelivery(
            organization_id=site.organization_id,
            endpoint_id=endpoint.id,
            site_id=site.id,
            event_type="test",
            payload={"webhook_secret": "must-never-export"},
            status="delivered",
            response_detail="private-token",
        )
    )
    db.commit()
    return sensor, job


def test_site_export_is_scoped_normalized_and_secret_free() -> None:
    db = make_session()
    organization, user, site = seed_workspace(db)
    seed_site_data(db, site)
    other_organization, other_user, other_site = seed_workspace(db, "bravo")
    seed_site_data(db, other_site)
    client = make_client(db)
    try:
        response = client.get(f"/api/v1/sites/{site.id}/export", headers=headers_for(organization, user))
        foreign = client.get(
            f"/api/v1/sites/{site.id}/export",
            headers=headers_for(other_organization, other_user),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-disposition"].endswith(f'{site.id}.json"')
    bundle = response.json()
    assert bundle["schema_version"] == "secopsai.edge.site-export.v1"
    assert bundle["site"]["id"] == site.id
    assert "token_hash" not in bundle["sensors"][0]
    assert "raw" not in bundle["asset_observations"][0]
    assert "raw_nmap" not in response.text
    assert "private-token" not in response.text
    assert "must-never-export" not in response.text
    assert bundle["notification_endpoints"][0]["target_redacted"] == "configured webhook (redacted)"
    assert "last_error" not in bundle["notification_endpoints"][0]
    assert "payload" not in bundle["notification_deliveries"][0]
    assert "response_detail" not in bundle["notification_deliveries"][0]
    assert bundle["audit_logs"][0]["details"]["api_token"] == "[redacted]"
    assert foreign.status_code == 404


def test_site_deletion_requires_owner_proof_and_no_active_jobs(monkeypatch) -> None:
    db = make_session()
    organization, user, site = seed_workspace(db)
    sensor, job = seed_site_data(db, site)
    site_id = site.id
    sensor_id = sensor.id
    headers = headers_for(organization, user)
    client = make_client(db)
    payload = {
        "confirmation": site.name,
        "current_password": PASSWORD,
        "acknowledge_permanent": True,
    }
    try:
        legacy = client.request(
            "DELETE",
            f"/api/v1/sites/{site_id}",
            headers={"Authorization": "Bearer dev-admin-token"},
            json=payload,
        )
        wrong = client.request(
            "DELETE",
            f"/api/v1/sites/{site_id}",
            headers=headers,
            json={**payload, "confirmation": "wrong"},
        )
        active = client.request("DELETE", f"/api/v1/sites/{site_id}", headers=headers, json=payload)
        assert active.status_code == 409

        job.status = "completed"
        job.updated_at = utcnow()
        user.mfa_enabled_at = utcnow()
        db.commit()
        missing_mfa = client.request(
            "DELETE", f"/api/v1/sites/{site_id}", headers=headers, json=payload
        )
        monkeypatch.setattr(main_module, "verify_mfa_code", lambda *args: True)
        deleted = client.request(
            "DELETE",
            f"/api/v1/sites/{site_id}",
            headers=headers,
            json={**payload, "code": "123456"},
        )
    finally:
        app.dependency_overrides.clear()

    assert legacy.status_code == 403
    assert wrong.status_code == 400
    assert missing_mfa.status_code == 403
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert db.get(Site, site_id) is None
    assert db.get(Sensor, sensor_id) is None
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "site.deleted"))
    assert audit is not None
    assert "name" not in audit.details


def test_retention_is_configurable_scoped_and_keeps_recent_data() -> None:
    db = make_session()
    organization, user, site = seed_workspace(db)
    sensor, job = seed_site_data(db, site)
    _, _, other_site = seed_workspace(db, "bravo")
    other_sensor, _ = seed_site_data(db, other_site)
    old = utcnow() - timedelta(days=10)
    recent = utcnow() - timedelta(days=1)
    asset = db.scalar(select(Asset).where(Asset.site_id == site.id))
    assert asset is not None
    old_scan = ScanRun(
        site_id=site.id,
        sensor_id=sensor.id,
        status="completed",
        completed_at=old,
    )
    recent_scan = ScanRun(
        site_id=site.id,
        sensor_id=sensor.id,
        status="completed",
        completed_at=recent,
    )
    db.add_all([old_scan, recent_scan])
    db.flush()
    old_observation = AssetObservation(
        site_id=site.id,
        sensor_id=sensor.id,
        scan_id=old_scan.id,
        asset_id=asset.id,
        ip_address=asset.ip_address,
        observed_at=old,
    )
    recent_observation = AssetObservation(
        site_id=site.id,
        sensor_id=sensor.id,
        scan_id=recent_scan.id,
        asset_id=asset.id,
        ip_address=asset.ip_address,
        observed_at=recent,
    )
    other_asset = db.scalar(select(Asset).where(Asset.site_id == other_site.id))
    assert other_asset is not None
    other_scan = ScanRun(
        site_id=other_site.id,
        sensor_id=other_sensor.id,
        status="completed",
        completed_at=old,
    )
    db.add(other_scan)
    db.flush()
    other_observation = AssetObservation(
        site_id=other_site.id,
        sensor_id=other_sensor.id,
        scan_id=other_scan.id,
        asset_id=other_asset.id,
        ip_address=other_asset.ip_address,
        observed_at=old,
    )
    db.add_all([old_observation, recent_observation, other_observation])
    job.status = "completed"
    job.updated_at = old
    db.commit()
    old_observation_id = old_observation.id
    recent_observation_id = recent_observation.id
    other_observation_id = other_observation.id
    old_scan_id = old_scan.id

    client = make_client(db)
    headers = headers_for(organization, user)
    policy_payload = {
        "observation_days": 7,
        "scan_history_days": 7,
        "notification_delivery_days": 7,
        "account_access_days": 1,
        "credential_history_days": 7,
        "report_days": 30,
        "audit_log_days": 90,
    }
    try:
        defaults = client.get("/api/v1/data-lifecycle", headers=headers)
        updated = client.patch("/api/v1/data-lifecycle", headers=headers, json=policy_payload)
        result = client.post("/api/v1/data-lifecycle/run-due", headers=headers)
        skipped = client.post("/api/v1/data-lifecycle/run-due", headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert defaults.status_code == 200
    assert defaults.json()["observation_days"] == 90
    assert updated.status_code == 200
    assert updated.json()["observation_days"] == 7
    assert result.status_code == 200
    assert result.json()["organizations"] == 1
    assert result.json()["skipped"] == 0
    assert skipped.json()["organizations"] == 0
    assert skipped.json()["skipped"] == 1
    assert result.json()["deleted"]["asset_observations"] >= 1
    assert db.get(AssetObservation, old_observation_id) is None
    assert db.get(ScanRun, old_scan_id) is None
    assert db.get(AssetObservation, recent_observation_id) is not None
    assert db.get(AssetObservation, other_observation_id) is not None
    policy = db.get(DataLifecyclePolicy, organization.id)
    assert policy is not None and policy.last_run_at is not None
