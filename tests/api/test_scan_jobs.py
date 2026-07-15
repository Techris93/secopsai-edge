from collections.abc import Generator
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
from secopsai_api.main import app
from secopsai_api.models import Base, ScanJob, Sensor, Site, utcnow
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


def seed_sensor(db: Session) -> tuple[Sensor, str]:
    sensor_token = "sensor-token"
    site = Site(name="Test Site")
    sensor = Sensor(site=site, name="MacBook Sensor", hostname="macbook", token_hash=hash_secret(sensor_token))
    db.add_all([site, sensor])
    db.commit()
    db.refresh(sensor)
    return sensor, sensor_token


def admin_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev-admin-token"}


def sensor_headers(sensor_token: str) -> dict[str, str]:
    return {"X-Sensor-Token": sensor_token}


def test_scan_job_rejects_public_ranges() -> None:
    db = make_session()
    seed_sensor(db)
    client = make_client(db)

    response = client.post(
        "/api/v1/scan-jobs",
        headers=admin_headers(),
        json={"target_cidr": "8.8.8.0/24"},
    )

    assert response.status_code == 400


def test_scan_job_claim_start_and_complete_from_scan_ingest() -> None:
    db = make_session()
    sensor, sensor_token = seed_sensor(db)
    client = make_client(db)

    create_response = client.post(
        "/api/v1/scan-jobs",
        headers=admin_headers(),
        json={"target_cidr": "192.168.1.0/24", "include_wifi": True},
    )
    assert create_response.status_code == 200
    job = create_response.json()
    assert job["status"] == "queued"
    assert job["sensor_id"] == sensor.id

    claim_response = client.post(
        f"/api/v1/sensors/{sensor.id}/scan-jobs/claim",
        headers=sensor_headers(sensor_token),
    )
    assert claim_response.status_code == 200
    assert claim_response.json()["status"] == "claimed"

    start_response = client.post(
        f"/api/v1/sensors/{sensor.id}/scan-jobs/{job['id']}/start",
        headers=sensor_headers(sensor_token),
        json={"preview": {"target_cidr": "192.168.1.0/24"}},
    )
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"

    ingest_response = client.post(
        "/api/v1/scans",
        headers=sensor_headers(sensor_token),
        json={
            "sensor_id": sensor.id,
            "scan_job_id": job["id"],
            "target_cidr": "192.168.1.0/24",
            "assets": [{"ip": "192.168.1.42", "vendor": "Apple"}],
            "wifi_networks": [],
        },
    )
    assert ingest_response.status_code == 200

    completed_job = db.scalar(select(ScanJob).where(ScanJob.id == job["id"]))
    assert completed_job is not None
    assert completed_job.status == "completed"
    assert completed_job.result_summary["assets_seen"] == 1


def test_claim_returns_null_when_no_jobs_are_queued() -> None:
    db = make_session()
    sensor, sensor_token = seed_sensor(db)
    client = make_client(db)

    response = client.post(
        f"/api/v1/sensors/{sensor.id}/scan-jobs/claim",
        headers=sensor_headers(sensor_token),
    )

    assert response.status_code == 200
    assert response.json() is None


def test_list_sensors_reports_online_state_and_current_job() -> None:
    db = make_session()
    sensor, _sensor_token = seed_sensor(db)
    sensor.status = "scanning"
    sensor.last_seen_at = utcnow()
    job = ScanJob(
        site_id=sensor.site_id,
        sensor_id=sensor.id,
        target_cidr="192.168.1.0/24",
        include_wifi=False,
        status="running",
    )
    db.add(job)
    db.commit()
    client = make_client(db)

    response = client.get("/api/v1/sensors", headers=admin_headers())

    assert response.status_code == 200
    sensors = response.json()
    assert sensors[0]["id"] == sensor.id
    assert sensors[0]["name"] == "MacBook Sensor"
    assert sensors[0]["site_name"] == "Test Site"
    assert sensors[0]["connection_state"] == "online"
    assert sensors[0]["recommended_version"]
    assert sensors[0]["release_status"] == "unknown"
    assert sensors[0]["upgrade_available"] is None
    assert sensors[0]["current_job"]["id"] == job.id
    assert sensors[0]["current_job"]["status"] == "running"


def test_list_sensors_marks_stale_sensor_offline() -> None:
    db = make_session()
    sensor, _sensor_token = seed_sensor(db)
    sensor.status = "online"
    sensor.last_seen_at = utcnow() - timedelta(minutes=10)
    db.commit()
    client = make_client(db)

    response = client.get("/api/v1/sensors", headers=admin_headers())

    assert response.status_code == 200
    assert response.json()[0]["connection_state"] == "offline"


def test_list_sensors_reports_outdated_release() -> None:
    db = make_session()
    sensor, _sensor_token = seed_sensor(db)
    sensor.version = "0.1.0"
    sensor.last_seen_at = utcnow()
    db.commit()
    client = make_client(db)

    response = client.get("/api/v1/sensors", headers=admin_headers())

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["release_status"] == "outdated"
    assert payload["upgrade_available"] is True


def test_list_sensors_marks_disabled_release_as_disabled() -> None:
    db = make_session()
    sensor, _sensor_token = seed_sensor(db)
    sensor.version = "0.1.0"
    sensor.disabled_at = utcnow()
    db.commit()
    client = make_client(db)

    response = client.get("/api/v1/sensors", headers=admin_headers())

    assert response.status_code == 200
    assert response.json()[0]["release_status"] == "disabled"
    assert response.json()[0]["upgrade_available"] is False


def test_retry_failed_scan_job_creates_new_queued_job() -> None:
    db = make_session()
    sensor, _sensor_token = seed_sensor(db)
    failed = ScanJob(
        site_id=sensor.site_id,
        sensor_id=sensor.id,
        target_cidr="192.168.1.0/24",
        include_wifi=True,
        status="failed",
        error_message="worker died",
    )
    db.add(failed)
    db.commit()
    client = make_client(db)

    response = client.post(f"/api/v1/scan-jobs/{failed.id}/retry", headers=admin_headers())

    assert response.status_code == 200
    retried = response.json()
    assert retried["id"] != failed.id
    assert retried["target_cidr"] == "192.168.1.0/24"
    assert retried["include_wifi"] is True
    assert retried["status"] == "queued"


def test_claim_recovers_stale_claimed_job_before_claiming_next() -> None:
    db = make_session()
    sensor, sensor_token = seed_sensor(db)
    stale = ScanJob(
        site_id=sensor.site_id,
        sensor_id=sensor.id,
        target_cidr="192.168.1.0/24",
        status="claimed",
        updated_at=utcnow() - timedelta(minutes=30),
    )
    db.add(stale)
    db.commit()
    client = make_client(db)

    response = client.post(
        f"/api/v1/sensors/{sensor.id}/scan-jobs/claim",
        headers=sensor_headers(sensor_token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == stale.id
    assert response.json()["status"] == "claimed"
