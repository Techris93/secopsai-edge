from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from secopsai_api.audit import write_audit
from secopsai_api.config import Settings
from secopsai_api.models import Sensor, Site, utcnow
from secopsai_api.notifications import notify_event


def mark_sensor_seen(sensor: Sensor, seen_at: datetime | None = None) -> datetime:
    """Record a healthy sensor signal and permit a future offline alert."""
    timestamp = seen_at or utcnow()
    sensor.last_seen_at = timestamp
    sensor.offline_alerted_at = None
    return timestamp


def evaluate_sensor_offline_alerts(
    db: Session,
    *,
    offline_after: timedelta,
    settings: Settings,
    now: datetime | None = None,
    organization_id: str | None = None,
) -> int:
    """Mark stale sensors offline and create one notification per outage."""
    current = now or utcnow()
    query = (
        select(Sensor, Site.organization_id)
        .join(Site, Site.id == Sensor.site_id)
        .where(
            Sensor.disabled_at.is_(None),
            Sensor.last_seen_at.is_not(None),
        )
        .order_by(Sensor.last_seen_at.asc())
    )
    if organization_id:
        query = query.where(Site.organization_id == organization_id)

    alerts_created = 0
    for sensor, sensor_organization_id in db.execute(query).all():
        last_seen = sensor.last_seen_at
        if last_seen is None:
            continue
        comparable_current = current.replace(tzinfo=None) if current.tzinfo else current
        comparable_last_seen = last_seen.replace(tzinfo=None) if last_seen.tzinfo else last_seen
        if comparable_current - comparable_last_seen < offline_after:
            continue

        sensor.status = "offline"
        if sensor.offline_alerted_at is not None:
            continue

        sensor.offline_alerted_at = current
        minutes_since_seen = max(1, int((comparable_current - comparable_last_seen).total_seconds() // 60))
        notify_event(
            db,
            "sensor_offline",
            {
                "title": "Sensor offline",
                "summary": f"Sensor {sensor.name} has not reported for {minutes_since_seen} minutes.",
                "sensor_id": sensor.id,
                "sensor_name": sensor.name,
                "site_id": sensor.site_id,
                "last_seen_at": last_seen.isoformat(),
                "offline_after_seconds": int(offline_after.total_seconds()),
            },
            site_id=sensor.site_id,
            settings=settings,
        )
        write_audit(
            db,
            "sensor.offline_alerted",
            sensor_id=sensor.id,
            organization_id=sensor_organization_id,
            resource_type="sensor",
            resource_id=sensor.id,
            details={
                "site_id": sensor.site_id,
                "last_seen_at": last_seen.isoformat(),
                "offline_after_seconds": int(offline_after.total_seconds()),
            },
        )
        alerts_created += 1

    db.flush()
    return alerts_created
