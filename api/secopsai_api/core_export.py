from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from secopsai_api import __version__

from secopsai_api.models import (
    Asset,
    AssetObservation,
    Finding,
    ScanRun,
    Sensor,
    Service,
    Site,
    WifiNetwork,
)


SCHEMA_VERSION = "secopsai.edge.bundle.v1"


def build_core_export(db: Session, organization_id: str | None = None) -> dict[str, Any]:
    """Build the normalized Edge bundle consumed by SecOpsAI Core."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    site_query = select(Site).order_by(Site.created_at.asc())
    if organization_id:
        site_query = site_query.where(Site.organization_id == organization_id)
    sites = list(db.scalars(site_query).all())
    site_ids = [site.id for site in sites]
    sensors = list(db.scalars(select(Sensor).where(Sensor.site_id.in_(site_ids)).order_by(Sensor.created_at.asc())).all())
    scans = list(db.scalars(select(ScanRun).where(ScanRun.site_id.in_(site_ids)).order_by(ScanRun.completed_at.asc())).all())
    assets = list(db.scalars(select(Asset).where(Asset.site_id.in_(site_ids)).order_by(Asset.last_seen_at.asc())).all())
    asset_ids = [asset.id for asset in assets]
    services = list(db.scalars(select(Service).where(Service.asset_id.in_(asset_ids)).order_by(Service.last_seen_at.asc())).all())
    wifi_networks = list(db.scalars(select(WifiNetwork).where(WifiNetwork.site_id.in_(site_ids)).order_by(WifiNetwork.last_seen_at.asc())).all())
    observations = list(db.scalars(select(AssetObservation).where(AssetObservation.site_id.in_(site_ids))).all())
    findings = list(db.scalars(select(Finding).where(Finding.site_id.in_(site_ids)).order_by(Finding.updated_at.asc())).all())

    for site in sites:
        nodes.append(
            _node(
                "site",
                site.id,
                label=site.name,
                properties={"name": site.name, "created_at": _iso(site.created_at)},
            )
        )

    for sensor in sensors:
        nodes.append(
            _node(
                "sensor",
                sensor.id,
                label=sensor.name,
                properties={
                    "site_id": sensor.site_id,
                    "name": sensor.name,
                    "hostname": sensor.hostname,
                    "status": sensor.status,
                    "created_at": _iso(sensor.created_at),
                    "last_seen_at": _iso(sensor.last_seen_at),
                },
            )
        )
        edges.append(_edge("site_has_sensor", _node_id("site", sensor.site_id), _node_id("sensor", sensor.id)))

    for scan in scans:
        nodes.append(
            _node(
                "scan",
                scan.id,
                label=scan.target_cidr or scan.id,
                properties={
                    "site_id": scan.site_id,
                    "sensor_id": scan.sensor_id,
                    "target_cidr": scan.target_cidr,
                    "scan_source": scan.scan_source,
                    "status": scan.status,
                    "started_at": _iso(scan.started_at),
                    "completed_at": _iso(scan.completed_at),
                    "summary": scan.summary or {},
                },
            )
        )
        edges.append(_edge("sensor_ran_scan", _node_id("sensor", scan.sensor_id), _node_id("scan", scan.id)))

    for asset in assets:
        nodes.append(
            _node(
                "asset",
                asset.id,
                label=asset.hostname or asset.ip_address,
                properties={
                    "site_id": asset.site_id,
                    "ip_address": asset.ip_address,
                    "mac_address": asset.mac_address,
                    "vendor": asset.vendor,
                    "hostname": asset.hostname,
                    "os_guess": asset.os_guess,
                    "device_type": asset.device_type,
                    "status": asset.status,
                    "first_seen_at": _iso(asset.first_seen_at),
                    "last_seen_at": _iso(asset.last_seen_at),
                },
            )
        )

    for service in services:
        service_local_id = f"{service.asset_id}:{service.protocol}:{service.port}"
        nodes.append(
            _node(
                "service",
                service_local_id,
                label=f"{service.protocol}/{service.port}",
                properties={
                    "asset_id": service.asset_id,
                    "port": service.port,
                    "protocol": service.protocol,
                    "name": service.name,
                    "product": service.product,
                    "version": service.version,
                    "state": service.state,
                    "first_seen_at": _iso(service.first_seen_at),
                    "last_seen_at": _iso(service.last_seen_at),
                },
            )
        )
        edges.append(
            _edge(
                "asset_exposes_service",
                _node_id("asset", service.asset_id),
                _node_id("service", service_local_id),
            )
        )

    for wifi in wifi_networks:
        nodes.append(
            _node(
                "wifi_network",
                wifi.id,
                label=wifi.ssid,
                properties={
                    "site_id": wifi.site_id,
                    "sensor_id": wifi.sensor_id,
                    "ssid": wifi.ssid,
                    "bssid": wifi.bssid,
                    "channel": wifi.channel,
                    "signal": wifi.signal,
                    "encryption": wifi.encryption,
                    "status": wifi.status,
                    "first_seen_at": _iso(wifi.first_seen_at),
                    "last_seen_at": _iso(wifi.last_seen_at),
                },
            )
        )
        edges.append(
            _edge(
                "sensor_observed_wifi",
                _node_id("sensor", wifi.sensor_id),
                _node_id("wifi_network", wifi.id),
            )
        )

    for observation in observations:
        edges.append(
            _edge(
                "scan_observed_asset",
                _node_id("scan", observation.scan_id),
                _node_id("asset", observation.asset_id),
                properties={"observed_at": _iso(observation.observed_at), "ip_address": observation.ip_address},
            )
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_instance": {
            "product": "secopsai_edge",
            "api": "secopsai-edge-api",
            "version": __version__,
            "organization_id": organization_id,
        },
        "cursor": _cursor(scans, findings),
        "graph": {
            "nodes": _dedupe_by_id(nodes),
            "edges": _dedupe_by_id(edges),
        },
        "findings": [_finding(finding) for finding in findings],
    }


def _cursor(scans: list[ScanRun], findings: list[Finding]) -> dict[str, Any]:
    timestamps = [
        item
        for item in [*(scan.completed_at for scan in scans), *(finding.updated_at for finding in findings)]
        if item is not None
    ]
    return {
        "mode": "full",
        "last_observed_at": _iso(max(timestamps)) if timestamps else None,
    }


def _node(node_type: str, local_id: str, *, label: str, properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _node_id(node_type, local_id),
        "type": node_type,
        "label": label,
        "source_id": str(local_id),
        "properties": _clean(properties),
    }


def _edge(
    edge_type: str,
    from_id: str,
    to_id: str,
    *,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    edge_id = f"edge:{edge_type}:{from_id}:{to_id}"
    return {
        "id": edge_id,
        "type": edge_type,
        "from": from_id,
        "to": to_id,
        "properties": _clean(properties or {}),
    }


def _node_id(node_type: str, local_id: str) -> str:
    return f"edge:{node_type}:{local_id}"


def _finding(finding: Finding) -> dict[str, Any]:
    return {
        "id": finding.id,
        "type": finding.type,
        "title": finding.title,
        "summary": finding.summary,
        "severity": finding.severity,
        "status": finding.status,
        "site_node_id": _node_id("site", finding.site_id),
        "asset_node_id": _node_id("asset", finding.asset_id) if finding.asset_id else None,
        "wifi_node_id": _node_id("wifi_network", finding.wifi_network_id) if finding.wifi_network_id else None,
        "evidence": _clean(finding.evidence or {}),
        "mitre_attack": finding.mitre_attack or [],
        "created_at": _iso(finding.created_at),
        "updated_at": _iso(finding.updated_at),
    }


def _dedupe_by_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in items:
        by_id[str(item["id"])] = item
    return list(by_id.values())


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    return value


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
