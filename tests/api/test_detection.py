from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from secopsai_api.detection import ingest_scan
from secopsai_api.models import Base, Finding, Sensor, Site
from secopsai_api.schemas import AssetObservationIn, ScanIn, ServiceIn, WifiNetworkIn


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def seed_sensor(db):
    site = Site(name="Test Site")
    sensor = Sensor(site=site, name="Test Sensor", hostname="test", token_hash="hash")
    db.add_all([site, sensor])
    db.commit()
    return sensor


def test_ingest_scan_creates_new_device_and_risky_port_findings() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    payload = ScanIn(
        sensor_id=sensor.id,
        target_cidr="192.168.1.0/24",
        assets=[
            AssetObservationIn(
                ip="192.168.1.50",
                vendor="Unknown",
                services=[ServiceIn(port=22, name="ssh")],
            )
        ],
    )

    _scan, findings = ingest_scan(db, sensor, payload)
    db.commit()

    finding_types = {finding.type for finding in findings}
    assert {"new_device", "vendor_unknown", "risky_open_port"}.issubset(finding_types)


def test_duplicate_ssid_with_new_bssid_creates_finding() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    first = ScanIn(
        sensor_id=sensor.id,
        wifi_networks=[
            WifiNetworkIn(ssid="OfficeWiFi", bssid="aa:aa:aa:aa:aa:aa", encryption="WPA2")
        ],
    )
    second = ScanIn(
        sensor_id=sensor.id,
        wifi_networks=[
            WifiNetworkIn(ssid="OfficeWiFi", bssid="bb:bb:bb:bb:bb:bb", encryption="WPA2")
        ],
    )

    ingest_scan(db, sensor, first)
    _scan, findings = ingest_scan(db, sensor, second)
    db.commit()

    assert any(finding.type == "duplicate_ssid" for finding in findings)


def test_missing_device_detection_marks_asset_missing() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    ingest_scan(
        db,
        sensor,
        ScanIn(
            sensor_id=sensor.id,
            target_cidr="192.168.1.0/24",
            assets=[AssetObservationIn(ip="192.168.1.20", vendor="Apple")],
        ),
    )

    _scan, findings = ingest_scan(
        db,
        sensor,
        ScanIn(sensor_id=sensor.id, target_cidr="192.168.1.0/24", assets=[]),
    )
    db.commit()

    assert any(finding.type == "missing_device" for finding in findings)
    assert db.scalar(select(Finding).where(Finding.type == "missing_device")) is not None


def test_multiple_port_changes_on_one_asset_remain_distinct() -> None:
    db = make_session()
    sensor = seed_sensor(db)
    ingest_scan(
        db,
        sensor,
        ScanIn(
            sensor_id=sensor.id,
            target_cidr="192.168.1.0/24",
            assets=[AssetObservationIn(ip="192.168.1.30", vendor="Apple", services=[])],
        ),
    )

    _scan, added = ingest_scan(
        db,
        sensor,
        ScanIn(
            sensor_id=sensor.id,
            target_cidr="192.168.1.0/24",
            assets=[
                AssetObservationIn(
                    ip="192.168.1.30",
                    vendor="Apple",
                    services=[ServiceIn(port=8080), ServiceIn(port=8443)],
                )
            ],
        ),
    )
    db.commit()

    added_changes = [finding for finding in added if finding.type == "port_change"]
    assert {finding.evidence["port"] for finding in added_changes} == {8080, 8443}
    assert len(db.scalars(select(Finding).where(Finding.type == "port_change")).all()) == 2

    _scan, removed = ingest_scan(
        db,
        sensor,
        ScanIn(
            sensor_id=sensor.id,
            target_cidr="192.168.1.0/24",
            assets=[AssetObservationIn(ip="192.168.1.30", vendor="Apple", services=[])],
        ),
    )
    db.commit()

    removed_changes = [finding for finding in removed if finding.type == "port_change"]
    assert {finding.evidence["port"] for finding in removed_changes} == {8080, 8443}
    assert all(finding.title == "Previously open port disappeared" for finding in removed_changes)
