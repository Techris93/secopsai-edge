from collections.abc import Generator
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
from secopsai_api.main import app, report_export_filename
from secopsai_api.models import Asset, AuditLog, Base, Finding, NotificationEndpoint, Report, ScanJob, ScanRun, ScanSchedule, Sensor, Site, utcnow
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

    enable_response = client.post(f"/api/v1/sensors/{sensor.id}/enable", headers=admin_headers())
    assert enable_response.status_code == 200
    assert enable_response.json()["connection_state"] != "disabled"


def test_heartbeat_tracks_runtime_state_without_audit_spam() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    client = make_client(db)
    payload = {
        "status": "online",
        "details": {
            "state": "scanning",
            "job_id": "job-123",
            "version": "0.1.0",
            "os": "Darwin 25",
            "hostname": "sensor-host",
        },
    }
    headers = {"X-Sensor-Token": "sensor-token"}

    assert client.post(f"/api/v1/sensors/{sensor.id}/heartbeat", headers=headers, json=payload).status_code == 200
    assert client.post(f"/api/v1/sensors/{sensor.id}/heartbeat", headers=headers, json=payload).status_code == 200
    db.refresh(sensor)
    assert sensor.worker_state == "scanning"
    assert sensor.current_job_id == "job-123"
    assert sensor.version == "0.1.0"
    assert sensor.hostname == "sensor-host"
    state_events = db.query(AuditLog).filter(AuditLog.action == "sensor.state_changed").all()
    assert len(state_events) == 1


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


def test_report_html_export_requires_admin_and_returns_branded_report() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    report = Report(
        site_id=sensor.site_id,
        title="Weekly Edge Risk Summary",
        summary="A new unmanaged device exposed SSH.",
        risk_level="high",
        content={
            "provider": "mock",
            "model": "deterministic",
            "recommended_actions": ["Verify device ownership.", "Review SSH authentication logs."],
            "findings": [
                {
                    "type": "risky_open_port",
                    "severity": "high",
                    "status": "open",
                    "title": "SSH exposed internally",
                    "summary": "192.168.1.42 exposes tcp/22.",
                    "raw_nmap": "<host>secret raw scan</host>",
                }
            ],
        },
    )
    db.add(report)
    db.commit()
    client = make_client(db)

    unauthorized = client.get(f"/api/v1/reports/{report.id}/export.html")
    assert unauthorized.status_code == 401

    response = client.get(f"/api/v1/reports/{report.id}/export.html", headers=admin_headers())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "attachment;" in response.headers["content-disposition"]
    assert "SecOpsAI Edge Report" in response.text
    assert "Weekly Edge Risk Summary" in response.text
    assert "Pilot Office" in response.text
    assert "Verify device ownership." in response.text
    assert "secret raw scan" not in response.text


def test_report_pdf_export_requires_auth_and_excludes_raw_scan_fields() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    now = utcnow()
    report = Report(
        site_id=sensor.site_id,
        title="Weekly Edge Risk Summary",
        period_start=now - timedelta(days=7),
        period_end=now,
        summary="A new unmanaged device exposed SSH.",
        risk_level="high",
        content={
            "provider": "mock",
            "model": "deterministic",
            "metrics": {
                "assets_total": 14,
                "new_devices": 1,
                "risky_services": 1,
                "wifi_security_findings": 0,
                "open_findings": 1,
                "acknowledged_findings": 0,
                "resolved_findings": 2,
                "scans_completed": 7,
                "severity": {"critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0},
            },
            "recommended_actions": ["Verify device ownership.", "Review SSH authentication logs."],
            "findings": [
                {
                    "type": "risky_open_port",
                    "severity": "high",
                    "status": "open",
                    "title": "SSH exposed internally",
                    "summary": "192.168.1.42 exposes tcp/22.",
                    "raw_nmap": "<host>secret raw scan</host>",
                }
            ],
        },
    )
    db.add(report)
    db.commit()
    client = make_client(db)

    unauthorized = client.get(f"/api/v1/reports/{report.id}/export.pdf")
    response = client.get(f"/api/v1/reports/{report.id}/export.pdf", headers=admin_headers())

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].endswith('weekly-edge-risk-summary.pdf"')
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 10_000
    assert b"secret raw scan" not in response.content


def test_report_export_filename_is_ascii_safe() -> None:
    report = Report(
        site_id="site-alpha",
        title="İstanbul Güvenlik Özeti 🔒",
        summary="Summary",
        risk_level="low",
        content={},
    )

    filename = report_export_filename(report, "pdf")

    assert filename == "istanbul-guvenlik-ozeti.pdf"
    assert filename.isascii()


def test_report_generation_freezes_period_and_operational_metrics() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    now = utcnow()
    db.add_all(
        [
            Asset(site_id=sensor.site_id, ip_address="192.168.1.10", status="active"),
            Asset(site_id=sensor.site_id, ip_address="192.168.1.11", status="missing"),
            Finding(
                site_id=sensor.site_id,
                type="new_device",
                severity="medium",
                status="open",
                title="New device",
                summary="A new asset appeared.",
                created_at=now - timedelta(days=1),
                updated_at=now - timedelta(days=1),
            ),
            Finding(
                site_id=sensor.site_id,
                type="risky_open_port",
                severity="high",
                status="acknowledged",
                title="SSH exposed",
                summary="An administrative service is exposed.",
                created_at=now - timedelta(days=2),
                updated_at=now - timedelta(days=2),
            ),
            Finding(
                site_id=sensor.site_id,
                type="vendor_unknown",
                severity="low",
                status="resolved",
                title="Vendor resolved",
                summary="The device owner was confirmed.",
                created_at=now - timedelta(days=3),
                updated_at=now - timedelta(hours=2),
            ),
            ScanRun(
                site_id=sensor.site_id,
                sensor_id=sensor.id,
                status="completed",
                completed_at=now - timedelta(hours=4),
            ),
        ]
    )
    db.commit()
    client = make_client(db)

    response = client.post(
        f"/api/v1/reports/generate?site_id={sensor.site_id}",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    report = response.json()
    metrics = report["content"]["metrics"]
    assert report["period_start"] is not None
    assert report["period_end"] is not None
    content_start = datetime.fromisoformat(report["content"]["period"]["start"])
    stored_start = datetime.fromisoformat(report["period_start"])
    assert content_start.replace(tzinfo=None) == stored_start.replace(tzinfo=None)
    assert metrics == {
        "assets_total": 2,
        "assets_active": 1,
        "new_devices": 1,
        "risky_services": 1,
        "wifi_security_findings": 0,
        "open_findings": 1,
        "acknowledged_findings": 1,
        "resolved_findings": 1,
        "scans_completed": 1,
        "severity": {"critical": 0, "high": 1, "medium": 1, "low": 0, "info": 0},
    }

    limited = client.post(
        f"/api/v1/reports/generate?site_id={sensor.site_id}",
        headers=admin_headers(),
    )
    assert limited.status_code == 429
    assert limited.headers["Retry-After"].isdigit()
    assert "rate limited" in limited.json()["detail"]
