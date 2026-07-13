from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from secopsai_api.models import ScanJob, ScanSchedule, Sensor, Site, utcnow


ALLOWED_FREQUENCIES = {"daily", "weekly"}


def parse_time_of_day(value: str) -> time:
    try:
        hour, minute = value.split(":", 1)
        return time(hour=int(hour), minute=int(minute))
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="time_of_day must be HH:MM",
        ) from exc


def normalize_frequency(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_FREQUENCIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="frequency must be daily or weekly",
        )
    return normalized


def normalize_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown timezone",
        ) from exc
    return value


def compute_next_run_at(
    *,
    frequency: str,
    time_of_day: str,
    timezone_name: str,
    day_of_week: int | None = None,
    after: datetime | None = None,
) -> datetime:
    frequency = normalize_frequency(frequency)
    local_time = parse_time_of_day(time_of_day)
    tz = ZoneInfo(normalize_timezone(timezone_name))
    now_utc = after or utcnow()
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    now_local = now_utc.astimezone(tz)

    candidate = datetime.combine(now_local.date(), local_time, tzinfo=tz)
    if frequency == "daily":
        if candidate <= now_local:
            candidate += timedelta(days=1)
        return candidate.astimezone(timezone.utc)

    target_weekday = now_local.weekday() if day_of_week is None else day_of_week
    days_ahead = (target_weekday - now_local.weekday()) % 7
    candidate = datetime.combine(now_local.date(), local_time, tzinfo=tz) + timedelta(days=days_ahead)
    if candidate <= now_local:
        candidate += timedelta(days=7)
    return candidate.astimezone(timezone.utc)


def pick_site_and_sensor(
    db: Session,
    site_id: str | None,
    sensor_id: str | None,
    organization_id: str | None = None,
) -> tuple[Site, Sensor]:
    if sensor_id:
        sensor = db.get(Sensor, sensor_id)
        if sensor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
        if sensor.disabled_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sensor is disabled")
        site = db.get(Site, sensor.site_id)
        if site is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor site not found")
        if site_id and site_id != site.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sensor does not belong to site")
        if organization_id and site.organization_id != organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
        return site, sensor

    query = select(Sensor).order_by(Sensor.created_at.asc())
    if site_id:
        query = query.where(Sensor.site_id == site_id)
    if organization_id:
        query = query.join(Site, Site.id == Sensor.site_id).where(
            Site.organization_id == organization_id
        )
    query = query.where(Sensor.disabled_at.is_(None))
    sensor = db.scalar(query)
    if sensor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Register an enabled sensor first")
    site = db.get(Site, sensor.site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor site not found")
    return site, sensor


def enqueue_due_schedules(
    db: Session,
    now: datetime | None = None,
    organization_id: str | None = None,
) -> list[ScanJob]:
    now = now or utcnow()
    query = (
        select(ScanSchedule)
        .where(
            ScanSchedule.enabled.is_(True),
            ScanSchedule.next_run_at.is_not(None),
            ScanSchedule.next_run_at <= now,
        )
        .order_by(ScanSchedule.next_run_at.asc())
    )
    if organization_id:
        query = query.join(Site, Site.id == ScanSchedule.site_id).where(
            Site.organization_id == organization_id
        )
    schedules = db.scalars(query).all()
    jobs: list[ScanJob] = []
    for schedule in schedules:
        sensor = db.get(Sensor, schedule.sensor_id)
        if sensor is None or sensor.disabled_at is not None:
            schedule.enabled = False
            schedule.updated_at = now
            continue
        job = ScanJob(
            site_id=schedule.site_id,
            sensor_id=schedule.sensor_id,
            schedule_id=schedule.id,
            target_cidr=schedule.target_cidr,
            include_wifi=schedule.include_wifi,
            status="queued",
            preview={},
            result_summary={},
        )
        db.add(job)
        jobs.append(job)
        schedule.last_run_at = now
        schedule.next_run_at = compute_next_run_at(
            frequency=schedule.frequency,
            time_of_day=schedule.time_of_day,
            timezone_name=schedule.timezone,
            day_of_week=schedule.day_of_week,
            after=now + timedelta(seconds=1),
        )
        schedule.updated_at = now
    db.flush()
    return jobs
