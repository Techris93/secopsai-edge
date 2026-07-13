from __future__ import annotations

from datetime import datetime
from ipaddress import ip_network
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from secopsai_api.baselines import is_baselined
from secopsai_api.models import (
    Asset,
    AssetObservation,
    Finding,
    ScanRun,
    Sensor,
    Service,
    WifiNetwork,
    utcnow,
)
from secopsai_api.schemas import AssetObservationIn, ScanIn, ServiceIn, WifiNetworkIn


RISKY_PORTS: dict[int, tuple[str, str]] = {
    22: ("medium", "SSH exposed internally"),
    23: ("high", "Telnet exposed internally"),
    445: ("high", "SMB exposed internally"),
    3306: ("medium", "MySQL exposed internally"),
    5432: ("medium", "PostgreSQL exposed internally"),
    5900: ("high", "VNC exposed internally"),
    6379: ("high", "Redis exposed internally"),
    3389: ("high", "RDP exposed internally"),
    9200: ("high", "Elasticsearch exposed internally"),
}

OPEN_WIFI_MARKERS = {"open", "none", "owe", "wep"}


def ingest_scan(db: Session, sensor: Sensor, payload: ScanIn) -> tuple[ScanRun, list[Finding]]:
    scan = ScanRun(
        site_id=sensor.site_id,
        sensor_id=sensor.id,
        target_cidr=payload.target_cidr,
        scan_source=payload.scan_source,
        started_at=payload.started_at,
        completed_at=payload.completed_at or utcnow(),
        summary={
            "assets_seen": len(payload.assets),
            "wifi_networks_seen": len(payload.wifi_networks),
        },
    )
    db.add(scan)
    db.flush()

    findings: list[Finding] = []
    current_asset_ids: set[str] = set()

    for observed_asset in payload.assets:
        asset, is_new = upsert_asset(db, sensor, scan, observed_asset)
        current_asset_ids.add(asset.id)
        if is_new and not is_baselined(
            db, sensor.site_id, "asset", "new_device", asset=asset
        ):
            findings.append(
                upsert_finding(
                    db,
                    sensor.site_id,
                    "new_device",
                    "New device detected",
                    f"A previously unseen device appeared at {asset.ip_address}.",
                    "medium",
                    {"ip": asset.ip_address, "mac": asset.mac_address, "vendor": asset.vendor},
                    asset_id=asset.id,
                    mitre=[{"id": "T1046", "name": "Network Service Discovery"}],
                )
            )
        if _is_unknown_vendor(asset.vendor) and not is_baselined(
            db, sensor.site_id, "asset", "vendor_unknown", asset=asset
        ):
            findings.append(
                upsert_finding(
                    db,
                    sensor.site_id,
                    "vendor_unknown",
                    "Device vendor could not be identified",
                    f"{asset.ip_address} has no recognized MAC vendor.",
                    "low",
                    {"ip": asset.ip_address, "mac": asset.mac_address},
                    asset_id=asset.id,
                )
            )
        findings.extend(sync_services(db, sensor.site_id, asset, observed_asset.services, is_new))

    findings.extend(mark_missing_assets(db, sensor.site_id, payload.target_cidr, current_asset_ids))

    for observed_wifi in payload.wifi_networks:
        wifi, is_new_bssid = upsert_wifi(db, sensor, observed_wifi)
        findings.extend(evaluate_wifi(db, sensor.site_id, wifi, observed_wifi, is_new_bssid))

    sensor.status = "online"
    sensor.last_seen_at = utcnow()
    return scan, [finding for finding in findings if finding is not None]


def upsert_asset(
    db: Session,
    sensor: Sensor,
    scan: ScanRun,
    observed: AssetObservationIn,
) -> tuple[Asset, bool]:
    asset = None
    if observed.mac:
        asset = db.scalar(
            select(Asset).where(Asset.site_id == sensor.site_id, Asset.mac_address == observed.mac)
        )
    if asset is None:
        asset = db.scalar(
            select(Asset).where(Asset.site_id == sensor.site_id, Asset.ip_address == observed.ip)
        )

    is_new = asset is None
    if asset is None:
        asset = Asset(site_id=sensor.site_id, ip_address=observed.ip)
        db.add(asset)

    asset.ip_address = observed.ip
    asset.mac_address = observed.mac or asset.mac_address
    asset.vendor = observed.vendor or asset.vendor
    asset.hostname = observed.hostname or asset.hostname
    asset.os_guess = observed.os_guess or asset.os_guess
    asset.device_type = observed.device_type or asset.device_type or infer_device_type(observed)
    asset.status = "active"
    asset.last_seen_at = observed.observed_at or utcnow()
    db.flush()

    db.add(
        AssetObservation(
            site_id=sensor.site_id,
            sensor_id=sensor.id,
            scan_id=scan.id,
            asset_id=asset.id,
            ip_address=observed.ip,
            mac_address=observed.mac,
            vendor=observed.vendor,
            hostname=observed.hostname,
            os_guess=observed.os_guess,
            raw_source="agent",
            observed_at=observed.observed_at or utcnow(),
            raw=_minimize_raw(observed.raw),
        )
    )
    return asset, is_new


def sync_services(
    db: Session,
    site_id: str,
    asset: Asset,
    observed_services: list[ServiceIn],
    asset_is_new: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    existing = {
        (service.port, service.protocol): service
        for service in db.scalars(select(Service).where(Service.asset_id == asset.id)).all()
    }
    observed_keys = set()

    for observed in observed_services:
        key = (observed.port, observed.protocol)
        observed_keys.add(key)
        service = existing.get(key)
        service_is_new = service is None or service.state != "open"
        if service is None:
            service = Service(asset_id=asset.id, port=observed.port, protocol=observed.protocol)
            db.add(service)
        service.name = observed.name or service.name
        service.product = observed.product or service.product
        service.version = observed.version or service.version
        service.state = observed.state
        service.last_seen_at = utcnow()

        if observed.port in RISKY_PORTS and not is_baselined(
            db,
            site_id,
            "service",
            "risky_open_port",
            asset=asset,
            service=service,
        ):
            severity, title = RISKY_PORTS[observed.port]
            findings.append(
                upsert_finding(
                    db,
                    site_id,
                    "risky_open_port",
                    title,
                    f"{asset.ip_address} exposes {observed.protocol}/{observed.port}.",
                    severity,
                    {
                        "ip": asset.ip_address,
                        "port": observed.port,
                        "protocol": observed.protocol,
                        "service": observed.name,
                    },
                    asset_id=asset.id,
                    mitre=[{"id": "T1046", "name": "Network Service Discovery"}],
                )
            )

        if service_is_new and not asset_is_new and not is_baselined(
            db,
            site_id,
            "service",
            "port_change",
            asset=asset,
            service=service,
        ):
            findings.append(
                upsert_finding(
                    db,
                    site_id,
                    "port_change",
                    "New open port detected",
                    f"{asset.ip_address} now exposes {observed.protocol}/{observed.port}.",
                    "medium",
                    {"ip": asset.ip_address, "port": observed.port, "protocol": observed.protocol},
                    asset_id=asset.id,
                )
            )

    for key, service in existing.items():
        if key not in observed_keys and service.state == "open":
            service.state = "closed"
            if not is_baselined(
                db,
                site_id,
                "service",
                "port_change",
                asset=asset,
                service=service,
            ):
                findings.append(
                    upsert_finding(
                        db,
                        site_id,
                        "port_change",
                        "Previously open port disappeared",
                        f"{asset.ip_address} no longer exposes {service.protocol}/{service.port}.",
                        "low",
                        {"ip": asset.ip_address, "port": service.port, "protocol": service.protocol},
                        asset_id=asset.id,
                    )
                )
    return findings


def mark_missing_assets(
    db: Session,
    site_id: str,
    target_cidr: str | None,
    current_asset_ids: set[str],
) -> list[Finding]:
    if not target_cidr:
        return []
    try:
        network = ip_network(target_cidr, strict=False)
    except ValueError:
        return []

    findings: list[Finding] = []
    assets = db.scalars(select(Asset).where(Asset.site_id == site_id, Asset.status == "active")).all()
    for asset in assets:
        if asset.id in current_asset_ids:
            continue
        try:
            in_scope = asset.ip_address and ip_network(f"{asset.ip_address}/32").subnet_of(network)
        except ValueError:
            in_scope = False
        if not in_scope:
            continue
        asset.status = "missing"
        if not is_baselined(db, site_id, "asset", "missing_device", asset=asset):
            findings.append(
                upsert_finding(
                    db,
                    site_id,
                    "missing_device",
                    "Previously seen device is missing",
                    f"{asset.ip_address} was not observed in the latest scan.",
                    "low",
                    {"ip": asset.ip_address, "last_seen_at": _iso(asset.last_seen_at)},
                    asset_id=asset.id,
                )
            )
    return findings


def upsert_wifi(
    db: Session,
    sensor: Sensor,
    observed: WifiNetworkIn,
) -> tuple[WifiNetwork, bool]:
    wifi = db.scalar(
        select(WifiNetwork).where(
            WifiNetwork.site_id == sensor.site_id,
            WifiNetwork.ssid == observed.ssid,
            WifiNetwork.bssid == observed.bssid,
        )
    )
    is_new = wifi is None
    if wifi is None:
        wifi = WifiNetwork(site_id=sensor.site_id, sensor_id=sensor.id, ssid=observed.ssid)
        db.add(wifi)
    wifi.bssid = observed.bssid
    wifi.channel = observed.channel
    wifi.signal = observed.signal
    wifi.encryption = observed.encryption
    wifi.status = "active"
    wifi.last_seen_at = observed.observed_at or utcnow()
    db.flush()
    return wifi, is_new


def evaluate_wifi(
    db: Session,
    site_id: str,
    wifi: WifiNetwork,
    observed: WifiNetworkIn,
    is_new_bssid: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    encryption = (observed.encryption or "").strip().lower()
    if (
        any(marker == encryption or marker in encryption for marker in OPEN_WIFI_MARKERS)
        and not is_baselined(db, site_id, "wifi", "weak_wifi", wifi=wifi)
    ):
        findings.append(
            upsert_finding(
                db,
                site_id,
                "weak_wifi",
                "Weak or open Wi-Fi network detected",
                f"{observed.ssid} is advertising weak or missing encryption.",
                "high",
                {
                    "ssid": observed.ssid,
                    "bssid": observed.bssid,
                    "encryption": observed.encryption,
                },
                wifi_network_id=wifi.id,
                mitre=[{"id": "T1557", "name": "Adversary-in-the-Middle"}],
            )
        )

    if is_new_bssid and observed.bssid:
        matching_ssids = db.scalars(
            select(WifiNetwork).where(
                WifiNetwork.site_id == site_id,
                WifiNetwork.ssid == observed.ssid,
                WifiNetwork.bssid != observed.bssid,
            )
        ).all()
        if matching_ssids and not is_baselined(
            db, site_id, "wifi", "duplicate_ssid", wifi=wifi
        ):
            findings.append(
                upsert_finding(
                    db,
                    site_id,
                    "duplicate_ssid",
                    "Duplicate SSID with new BSSID detected",
                    f"{observed.ssid} appeared with a new BSSID.",
                    "medium",
                    {
                        "ssid": observed.ssid,
                        "new_bssid": observed.bssid,
                        "known_bssids": [network.bssid for network in matching_ssids],
                    },
                    wifi_network_id=wifi.id,
                    mitre=[{"id": "T1557", "name": "Adversary-in-the-Middle"}],
                )
            )
    return findings


def upsert_finding(
    db: Session,
    site_id: str,
    finding_type: str,
    title: str,
    summary: str,
    severity: str,
    evidence: dict[str, Any],
    *,
    asset_id: str | None = None,
    wifi_network_id: str | None = None,
    mitre: list[dict[str, Any]] | None = None,
) -> Finding:
    candidates = db.scalars(
        select(Finding).where(
            Finding.site_id == site_id,
            Finding.type == finding_type,
            Finding.title == title,
            Finding.asset_id == asset_id,
            Finding.wifi_network_id == wifi_network_id,
            Finding.status.in_(["open", "acknowledged"]),
        )
    ).all()
    identity = _finding_identity(finding_type, evidence)
    existing = next(
        (
            candidate
            for candidate in candidates
            if identity is None or _finding_identity(candidate.type, candidate.evidence or {}) == identity
        ),
        None,
    )
    if existing:
        existing.evidence = evidence
        existing.summary = summary
        existing.severity = severity
        existing.updated_at = utcnow()
        return existing

    finding = Finding(
        site_id=site_id,
        asset_id=asset_id,
        wifi_network_id=wifi_network_id,
        type=finding_type,
        title=title,
        summary=summary,
        severity=severity,
        evidence=evidence,
        mitre_attack=mitre or [],
    )
    db.add(finding)
    db.flush()
    return finding


def _finding_identity(finding_type: str, evidence: dict[str, Any]) -> tuple[Any, ...] | None:
    if finding_type == "port_change":
        return (
            str(evidence.get("ip") or ""),
            int(evidence.get("port") or 0),
            str(evidence.get("protocol") or "tcp").lower(),
        )
    return None


def infer_device_type(observed: AssetObservationIn) -> str | None:
    joined = " ".join(
        item for item in [observed.vendor, observed.hostname, observed.os_guess] if item
    ).lower()
    if any(marker in joined for marker in ["printer", "hp ", "brother", "canon"]):
        return "printer"
    if any(marker in joined for marker in ["iphone", "android", "samsung"]):
        return "mobile"
    if any(marker in joined for marker in ["camera", "axis", "hikvision"]):
        return "camera"
    if any(marker in joined for marker in ["apple", "macbook", "windows", "linux"]):
        return "workstation"
    return None


def _is_unknown_vendor(vendor: str | None) -> bool:
    return vendor is None or vendor.strip().lower() in {"", "unknown", "n/a"}


def _minimize_raw(raw: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {"source", "scanner_version", "interface"}
    return {key: value for key, value in raw.items() if key in allowed_keys}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
