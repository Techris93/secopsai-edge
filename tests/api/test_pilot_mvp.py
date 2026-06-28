from collections.abc import Generator
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
from secopsai_api.main import app
from secopsai_api.models import Asset, Base, Finding, NotificationEndpoint, ScanJob, ScanRun, ScanSchedule, Sensor, Site, utcnow
from secopsai_api.security import hash_secret


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


def admin_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev-admin-token"}


def seed_sensor(db: Session) -> Sensor:
    site = Site(name="Pilot Office")
    sensor = Sensor(site=site, name="MacBook Sensor", hostname="macbook", token_hash=hash_secret("sensor-token"))
    db.add_all([site, sensor])
    db.commit()
    db.refresh(sensor)
    return sensor


def test_scan_schedule_can_enqueue_due_job() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    client = make_client(db)

    response = client.post(
        "/api/v1/scan-schedules",
        headers=admin_headers(),
        json={
            "name": "Daily scan",
            "sensor_id": sensor.id,
            "target_cidr": "192.168.1.0/24",
            "frequency": "daily",
            "time_of_day": "09:00",
            "timezone": "UTC",
        },
    )
    assert response.status_code == 200
    schedule_id = response.json()["id"]
    schedule = db.get(ScanSchedule, schedule_id)
    assert schedule is not None
    schedule.next_run_at = utcnow() - timedelta(minutes=1)
    db.commit()

    due_response = client.post("/api/v1/scan-schedules/run-due", headers=admin_headers())

    assert due_response.status_code == 200
    assert due_response.json()["queued"] == 1
    job = db.scalar(select(ScanJob).where(ScanJob.schedule_id == schedule_id))
    assert job is not None
    assert job.target_cidr == "192.168.1.0/24"


def test_finding_notes_and_verify_fixed_queue_rescan() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    asset = Asset(site_id=sensor.site_id, ip_address="192.168.1.42")
    db.add(asset)
    db.flush()
    finding = Finding(
        site_id=sensor.site_id,
        asset_id=asset.id,
        type="risky_open_port",
        severity="high",
        title="SSH exposed internally",
        summary="192.168.1.42 exposes tcp/22.",
        evidence={"ip": "192.168.1.42", "port": 22},
    )
    db.add(finding)
    db.commit()
    client = make_client(db)

    note_response = client.post(
        f"/api/v1/findings/{finding.id}/notes",
        headers=admin_headers(),
        json={"body": "Owner confirmed remediation is in progress."},
    )
    assert note_response.status_code == 200
    assert note_response.json()["body"].startswith("Owner confirmed")

    verify_response = client.post(f"/api/v1/findings/{finding.id}/verify", headers=admin_headers())

    assert verify_response.status_code == 200
    assert verify_response.json()["target_cidr"] == "192.168.1.0/24"
    assert verify_response.json()["status"] == "queued"


def test_sensor_rotation_and_disable() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    client = make_client(db)

    rotate_response = client.post(f"/api/v1/sensors/{sensor.id}/rotate-token", headers=admin_headers())

    assert rotate_response.status_code == 200
    assert rotate_response.json()["sensor_token"]
    assert rotate_response.json()["sensor_id"] == sensor.id

    disable_response = client.post(f"/api/v1/sensors/{sensor.id}/disable", headers=admin_headers())

    assert disable_response.status_code == 200
    assert disable_response.json()["connection_state"] == "disabled"


def test_onboarding_status_tracks_pilot_readiness() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    sensor.last_seen_at = utcnow()
    db.add(
        ScanRun(
            site_id=sensor.site_id,
            sensor_id=sensor.id,
            status="completed",
            summary={},
        )
    )
    db.add(
        NotificationEndpoint(
            site_id=sensor.site_id,
            name="Webhook",
            type="webhook",
            target="https://example.test/webhook",
            enabled=True,
            events=[],
        )
    )
    db.commit()
    client = make_client(db)

    response = client.get("/api/v1/onboarding/status", headers=admin_headers())

    assert response.status_code == 200
    status = response.json()
    assert status["sites_created"] is True
    assert status["sensor_registered"] is True
    assert status["worker_online"] is True
    assert status["first_scan_completed"] is True
    assert status["notifications_configured"] is True


def test_notification_endpoint_crud_without_delivery() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    client = make_client(db)

    create_response = client.post(
        "/api/v1/notification-endpoints",
        headers=admin_headers(),
        json={
            "site_id": sensor.site_id,
            "name": "Webhook",
            "type": "webhook",
            "target": "https://example.test/webhook",
            "events": ["high_finding"],
            "enabled": True,
        },
    )
    assert create_response.status_code == 200
    endpoint_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/v1/notification-endpoints/{endpoint_id}",
        headers=admin_headers(),
        json={"enabled": False},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["enabled"] is False

    delete_response = client.delete(f"/api/v1/notification-endpoints/{endpoint_id}", headers=admin_headers())
    assert delete_response.status_code == 200
