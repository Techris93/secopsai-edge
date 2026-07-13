from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from secopsai_api.models import (
    Asset,
    AssetObservation,
    AuditLog,
    BaselineRule,
    Finding,
    FindingNote,
    NotificationDelivery,
    NotificationEndpoint,
    Report,
    ScanJob,
    ScanRun,
    ScanSchedule,
    Sensor,
    SensorEnrollment,
    Service,
    Site,
    WifiNetwork,
    utcnow,
)


def build_site_export(db: Session, site: Site) -> dict[str, Any]:
    sensors = _rows(db, Sensor, Sensor.site_id == site.id)
    assets = _rows(db, Asset, Asset.site_id == site.id)
    asset_ids = [row.id for row in assets]
    findings = _rows(db, Finding, Finding.site_id == site.id)
    finding_ids = [row.id for row in findings]
    services = _rows(db, Service, Service.asset_id.in_(asset_ids)) if asset_ids else []
    sensor_enrollments = _rows(db, SensorEnrollment, SensorEnrollment.site_id == site.id)
    scan_runs = _rows(db, ScanRun, ScanRun.site_id == site.id)
    scan_jobs = _rows(db, ScanJob, ScanJob.site_id == site.id)
    scan_schedules = _rows(db, ScanSchedule, ScanSchedule.site_id == site.id)
    observations = _rows(db, AssetObservation, AssetObservation.site_id == site.id)
    wifi_networks = _rows(db, WifiNetwork, WifiNetwork.site_id == site.id)
    baselines = _rows(db, BaselineRule, BaselineRule.site_id == site.id)
    finding_notes = (
        _rows(db, FindingNote, FindingNote.finding_id.in_(finding_ids))
        if finding_ids
        else []
    )
    reports = _rows(db, Report, Report.site_id == site.id)
    notification_endpoints = _rows(
        db, NotificationEndpoint, NotificationEndpoint.site_id == site.id
    )
    endpoint_ids = [row.id for row in notification_endpoints]
    notification_deliveries = _rows(
        db,
        NotificationDelivery,
        or_(
            NotificationDelivery.site_id == site.id,
            NotificationDelivery.endpoint_id.in_(endpoint_ids) if endpoint_ids else False,
        ),
    )
    owned_rows = [
        site,
        *sensors,
        *sensor_enrollments,
        *scan_runs,
        *scan_jobs,
        *scan_schedules,
        *assets,
        *observations,
        *services,
        *wifi_networks,
        *baselines,
        *findings,
        *finding_notes,
        *reports,
        *notification_endpoints,
        *notification_deliveries,
    ]
    owned_resource_ids = [row.id for row in owned_rows]
    sensor_ids = [row.id for row in sensors]
    audit_logs = _rows(
        db,
        AuditLog,
        (AuditLog.organization_id == site.organization_id)
        & or_(
            AuditLog.resource_id.in_(owned_resource_ids),
            AuditLog.sensor_id.in_(sensor_ids) if sensor_ids else False,
        ),
    )

    return {
        "schema_version": "secopsai.edge.site-export.v1",
        "exported_at": utcnow().isoformat(),
        "site": _serialize(site),
        "sensors": [_serialize(row, exclude={"token_hash"}) for row in sensors],
        "sensor_enrollments": [
            _serialize(row, exclude={"token_hash"}) for row in sensor_enrollments
        ],
        "scan_runs": [_serialize(row) for row in scan_runs],
        "scan_jobs": [_serialize(row) for row in scan_jobs],
        "scan_schedules": [_serialize(row) for row in scan_schedules],
        "assets": [_serialize(row) for row in assets],
        "asset_observations": [
            _serialize(row, exclude={"raw"}) for row in observations
        ],
        "services": [_serialize(row) for row in services],
        "wifi_networks": [_serialize(row) for row in wifi_networks],
        "baselines": [_serialize(row) for row in baselines],
        "findings": [_serialize(row) for row in findings],
        "finding_notes": [_serialize(row) for row in finding_notes],
        "reports": [_serialize(row) for row in reports],
        "notification_endpoints": [
            {
                **_serialize(row, exclude={"target", "last_error"}),
                "target_redacted": _redact_target(row),
            }
            for row in notification_endpoints
        ],
        "notification_deliveries": [
            _serialize(row, exclude={"payload", "response_detail"})
            for row in notification_deliveries
        ],
        "audit_logs": [
            {
                **_serialize(row, exclude={"details"}),
                "details": _redact_secret_fields(row.details),
            }
            for row in audit_logs
        ],
    }


def _rows(db: Session, model, condition):
    return list(db.scalars(select(model).where(condition).order_by(model.id)).all())


def _serialize(row, *, exclude: set[str] | None = None) -> dict[str, Any]:
    excluded = exclude or set()
    output: dict[str, Any] = {}
    for column in inspect(row).mapper.column_attrs:
        key = column.key
        if key in excluded:
            continue
        value = getattr(row, key)
        output[key] = value.isoformat() if isinstance(value, datetime) else value
    return output


def _redact_target(endpoint: NotificationEndpoint) -> str:
    if endpoint.type == "email" and "@" in endpoint.target:
        local, domain = endpoint.target.rsplit("@", 1)
        return f"{local[:1]}***@{domain}"
    if endpoint.type == "webhook":
        return "configured webhook (redacted)"
    return "configured destination (redacted)"


def _redact_secret_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if _is_secret_key(key) else _redact_secret_fields(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_secret_fields(item) for item in value]
    return value


def _is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(
        marker in normalized
        for marker in ("password", "secret", "token", "recovery_code", "mfa_code")
    )
