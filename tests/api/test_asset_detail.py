import json
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
from secopsai_api.detection import ingest_scan
from secopsai_api.main import app
from secopsai_api.models import Asset, Base, Sensor, Site
from secopsai_api.schemas import AssetObservationIn, ScanIn, ServiceIn
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


def seed_asset(db: Session) -> Asset:
    site = Site(name="Pilot Office")
    sensor = Sensor(site=site, name="MacBook Sensor", hostname="macbook", token_hash=hash_secret("sensor-token"))
    db.add_all([site, sensor])
    db.commit()
    db.refresh(sensor)
    ingest_scan(
        db,
        sensor,
        ScanIn(
            sensor_id=sensor.id,
            target_cidr="192.168.1.0/24",
            scan_source="macos:test",
            assets=[
                AssetObservationIn(
                    ip="192.168.1.50",
                    mac="aa:bb:cc:dd:ee:ff",
                    vendor="Unknown",
                    hostname="pilot-host",
                    os_guess="Linux",
                    services=[ServiceIn(port=22, name="ssh")],
                    raw={"full_nmap_xml": "<host>secret raw scan</host>", "source": "nmap"},
                )
            ],
        ),
    )
    db.commit()
    asset = db.scalar(select(Asset).where(Asset.ip_address == "192.168.1.50"))
    assert asset is not None
    return asset


def test_asset_detail_returns_timeline_findings_and_normalized_observations() -> None:
    db = make_session()
    asset = seed_asset(db)
    client = make_client(db)

    try:
        response = client.get(f"/api/v1/assets/{asset.id}", headers=admin_headers())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"]["id"] == asset.id
    assert payload["asset"]["ip_address"] == "192.168.1.50"
    assert payload["observations"][0]["hostname"] == "pilot-host"
    assert payload["findings"]

    timeline_kinds = {event["kind"] for event in payload["timeline"]}
    assert {"asset_first_seen", "asset_observed", "service_observed", "finding_created"}.issubset(timeline_kinds)

    serialized = json.dumps(payload)
    assert "full_nmap_xml" not in serialized
    assert "secret raw scan" not in serialized


def test_asset_detail_requires_admin() -> None:
    db = make_session()
    asset = seed_asset(db)
    client = make_client(db)

    try:
        response = client.get(f"/api/v1/assets/{asset.id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
