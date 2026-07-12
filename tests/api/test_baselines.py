from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
from secopsai_api.detection import ingest_scan
from secopsai_api.main import app
from secopsai_api.models import AuditLog, Base, Finding, Sensor, Service, Site, WifiNetwork
from secopsai_api.schemas import AssetObservationIn, ScanIn, ServiceIn, WifiNetworkIn
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
    site = Site(name="Baseline Office")
    sensor = Sensor(site=site, name="MacBook Sensor", hostname="macbook", token_hash=hash_secret("sensor-token"))
    db.add_all([site, sensor])
    db.commit()
    db.refresh(sensor)
    return sensor


def test_asset_and_service_baselines_acknowledge_noise_and_suppress_future_findings() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    scan = ScanIn(
        sensor_id=sensor.id,
        target_cidr="192.168.1.0/24",
        assets=[
            AssetObservationIn(
                ip="192.168.1.50",
                mac="aa:bb:cc:dd:ee:ff",
                vendor="Unknown",
                services=[ServiceIn(port=22, name="ssh")],
            )
        ],
    )
    ingest_scan(db, sensor, scan)
    db.commit()
    asset_finding = db.scalar(select(Finding).where(Finding.type == "new_device"))
    service = db.scalar(select(Service).where(Service.port == 22))
    assert asset_finding is not None
    assert service is not None
    asset_id = asset_finding.asset_id
    assert asset_id is not None
    client = make_client(db)

    try:
        asset_response = client.post(
            f"/api/v1/assets/{asset_id}/baseline",
            headers=admin_headers(),
            json={"reason": "Managed employee laptop"},
        )
        assert asset_response.status_code == 200
        assert asset_response.json()["finding_types"] == ["new_device", "vendor_unknown"]

        service_response = client.post(
            f"/api/v1/services/{service.id}/baseline",
            headers=admin_headers(),
            json={"reason": "SSH is approved for administration"},
        )
        assert service_response.status_code == 200
        service_rule_id = service_response.json()["id"]

        db.expire_all()
        acknowledged = db.scalars(select(Finding).where(Finding.status == "acknowledged")).all()
        assert {finding.type for finding in acknowledged} == {"new_device", "vendor_unknown", "risky_open_port"}
        assert all((finding.evidence or {}).get("baseline", {}).get("rule_id") for finding in acknowledged)

        _scan, second_findings = ingest_scan(db, sensor, scan)
        db.commit()
        assert not {"new_device", "vendor_unknown", "risky_open_port", "port_change"}.intersection(
            finding.type for finding in second_findings
        )

        list_response = client.get("/api/v1/baselines", headers=admin_headers())
        assert list_response.status_code == 200
        assert len(list_response.json()) == 2

        disable_response = client.delete(
            f"/api/v1/baselines/{service_rule_id}",
            headers=admin_headers(),
        )
        assert disable_response.status_code == 200
        assert disable_response.json()["status"] == "disabled"
        db.expire_all()
        risky = db.scalar(select(Finding).where(Finding.type == "risky_open_port"))
        assert risky is not None
        assert risky.status == "open"
        assert "baseline" not in (risky.evidence or {})
        assert db.scalar(select(AuditLog).where(AuditLog.action == "baseline.disabled")) is not None
    finally:
        app.dependency_overrides.clear()


def test_trusted_bssid_suppresses_duplicate_ssid_but_not_weak_encryption() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    ingest_scan(
        db,
        sensor,
        ScanIn(
            sensor_id=sensor.id,
            wifi_networks=[WifiNetworkIn(ssid="OfficeWiFi", bssid="aa:aa:aa:aa:aa:aa", encryption="WPA2")],
        ),
    )
    db.commit()
    client = make_client(db)

    try:
        response = client.post(
            "/api/v1/baselines",
            headers=admin_headers(),
            json={
                "site_id": sensor.site_id,
                "kind": "wifi",
                "matcher": {"bssid": "bb:bb:bb:bb:bb:bb"},
                "finding_types": ["duplicate_ssid"],
                "reason": "Approved secondary office access point",
            },
        )
        assert response.status_code == 200

        _scan, findings = ingest_scan(
            db,
            sensor,
            ScanIn(
                sensor_id=sensor.id,
                wifi_networks=[WifiNetworkIn(ssid="OfficeWiFi", bssid="bb:bb:bb:bb:bb:bb", encryption="Open")],
            ),
        )
        db.commit()
        finding_types = {finding.type for finding in findings}
        assert "duplicate_ssid" not in finding_types
        assert "weak_wifi" in finding_types
        assert db.scalar(select(WifiNetwork).where(WifiNetwork.bssid == "bb:bb:bb:bb:bb:bb")) is not None
    finally:
        app.dependency_overrides.clear()


def test_baseline_rejects_unsafe_broad_matcher_and_wrong_finding_type() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    client = make_client(db)

    try:
        broad = client.post(
            "/api/v1/baselines",
            headers=admin_headers(),
            json={
                "site_id": sensor.site_id,
                "kind": "asset",
                "matcher": {},
                "finding_types": ["new_device"],
            },
        )
        assert broad.status_code == 400

        wrong_type = client.post(
            "/api/v1/baselines",
            headers=admin_headers(),
            json={
                "site_id": sensor.site_id,
                "kind": "asset",
                "matcher": {"ip_address": "192.168.1.5"},
                "finding_types": ["weak_wifi"],
            },
        )
        assert wrong_type.status_code == 400
    finally:
        app.dependency_overrides.clear()
