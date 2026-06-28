import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.core_export import build_core_export
from secopsai_api.database import get_db
from secopsai_api.detection import ingest_scan
from secopsai_api.main import app
from secopsai_api.models import Base, Sensor, Site
from secopsai_api.schemas import AssetObservationIn, ScanIn, ServiceIn, WifiNetworkIn
from secopsai_api.security import hash_secret


def make_session():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def seed_scan(db):
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
                    hostname="test-host",
                    services=[ServiceIn(port=22, name="ssh")],
                    raw={"full_nmap_xml": "<host>secret raw scan</host>", "source": "nmap"},
                )
            ],
            wifi_networks=[
                WifiNetworkIn(
                    ssid="OfficeWiFi",
                    bssid="11:22:33:44:55:66",
                    channel=6,
                    signal=-45,
                    encryption="WPA2",
                )
            ],
        ),
    )
    db.commit()
    return sensor


def test_core_export_bundle_contains_graph_and_findings_without_raw_scan_logs() -> None:
    db = make_session()
    seed_scan(db)

    bundle = build_core_export(db)

    assert bundle["schema_version"] == "secopsai.edge.bundle.v1"
    assert bundle["cursor"]["mode"] == "full"

    node_types = {node["type"] for node in bundle["graph"]["nodes"]}
    assert {"site", "sensor", "scan", "asset", "service", "wifi_network"}.issubset(node_types)

    edge_types = {edge["type"] for edge in bundle["graph"]["edges"]}
    assert {"site_has_sensor", "sensor_ran_scan", "scan_observed_asset", "asset_exposes_service", "sensor_observed_wifi"}.issubset(edge_types)

    finding_types = {finding["type"] for finding in bundle["findings"]}
    assert {"new_device", "vendor_unknown", "risky_open_port"}.issubset(finding_types)

    serialized = json.dumps(bundle)
    assert "full_nmap_xml" not in serialized
    assert "secret raw scan" not in serialized


def test_core_export_endpoint_requires_admin_and_returns_bundle() -> None:
    db = make_session()
    seed_scan(db)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        unauthorized = client.get("/api/v1/core/export")
        assert unauthorized.status_code == 401

        response = client.get("/api/v1/core/export", headers={"Authorization": "Bearer dev-admin-token"})
        assert response.status_code == 200
        assert response.json()["schema_version"] == "secopsai.edge.bundle.v1"
    finally:
        app.dependency_overrides.clear()
