from __future__ import annotations

from collections import Counter
from datetime import timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from secopsai_api.models import (
    AccountAccessToken,
    Asset,
    AssetObservation,
    AuditLog,
    BaselineRule,
    DataLifecyclePolicy,
    Finding,
    FindingNote,
    IntegrationToken,
    NotificationDelivery,
    NotificationEndpoint,
    Organization,
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


TERMINAL_JOB_STATUSES = ("completed", "failed", "canceled")
TERMINAL_DELIVERY_STATUSES = ("delivered", "failed")


def get_or_create_policy(db: Session, organization_id: str) -> DataLifecyclePolicy:
    policy = db.get(DataLifecyclePolicy, organization_id)
    if policy is None:
        policy = DataLifecyclePolicy(organization_id=organization_id)
        db.add(policy)
        db.flush()
    return policy


def run_retention(
    db: Session,
    *,
    organization_id: str | None = None,
    force: bool = False,
) -> dict[str, object]:
    now = utcnow()
    organization_query = select(Organization.id).where(Organization.active.is_(True))
    if organization_id:
        organization_query = organization_query.where(Organization.id == organization_id)
    organization_ids = list(db.scalars(organization_query).all())
    totals: Counter[str] = Counter()
    skipped = 0
    processed = 0

    for current_organization_id in organization_ids:
        policy = get_or_create_policy(db, current_organization_id)
        if not force and policy.last_run_at is not None:
            comparison_now = now if policy.last_run_at.tzinfo else now.replace(tzinfo=None)
            if comparison_now - policy.last_run_at < timedelta(hours=24):
                skipped += 1
                continue
        processed += 1
        site_ids = list(
            db.scalars(
                select(Site.id).where(Site.organization_id == current_organization_id)
            ).all()
        )
        if site_ids:
            observation_cutoff = now - timedelta(days=policy.observation_days)
            totals["asset_observations"] += _execute_delete(
                db,
                delete(AssetObservation).where(
                    AssetObservation.site_id.in_(site_ids),
                    AssetObservation.observed_at < observation_cutoff,
                ),
            )

            scan_cutoff = now - timedelta(days=policy.scan_history_days)
            old_run_ids = list(
                db.scalars(
                    select(ScanRun.id).where(
                        ScanRun.site_id.in_(site_ids),
                        ScanRun.completed_at.is_not(None),
                        ScanRun.completed_at < scan_cutoff,
                    )
                ).all()
            )
            if old_run_ids:
                totals["asset_observations"] += _execute_delete(
                    db,
                    delete(AssetObservation).where(
                        AssetObservation.scan_id.in_(old_run_ids)
                    ),
                )
                totals["scan_runs"] += _execute_delete(
                    db, delete(ScanRun).where(ScanRun.id.in_(old_run_ids))
                )
            totals["scan_jobs"] += _execute_delete(
                db,
                delete(ScanJob).where(
                    ScanJob.site_id.in_(site_ids),
                    ScanJob.status.in_(TERMINAL_JOB_STATUSES),
                    ScanJob.updated_at < scan_cutoff,
                ),
            )
            totals["reports"] += _execute_delete(
                db,
                delete(Report).where(
                    Report.site_id.in_(site_ids),
                    Report.created_at < now - timedelta(days=policy.report_days),
                ),
            )

        totals["notification_deliveries"] += _execute_delete(
            db,
            delete(NotificationDelivery).where(
                NotificationDelivery.organization_id == current_organization_id,
                NotificationDelivery.status.in_(TERMINAL_DELIVERY_STATUSES),
                NotificationDelivery.updated_at
                < now - timedelta(days=policy.notification_delivery_days),
            ),
        )
        totals["account_access_tokens"] += _execute_delete(
            db,
            delete(AccountAccessToken).where(
                AccountAccessToken.organization_id == current_organization_id,
                AccountAccessToken.expires_at
                < now - timedelta(days=policy.account_access_days),
            ),
        )
        credential_cutoff = now - timedelta(days=policy.credential_history_days)
        totals["sensor_enrollments"] += _execute_delete(
            db,
            delete(SensorEnrollment).where(
                SensorEnrollment.organization_id == current_organization_id,
                SensorEnrollment.expires_at < credential_cutoff,
                or_(
                    SensorEnrollment.used_at.is_not(None),
                    SensorEnrollment.revoked_at.is_not(None),
                    SensorEnrollment.expires_at < now,
                ),
            ),
        )
        totals["integration_tokens"] += _execute_delete(
            db,
            delete(IntegrationToken).where(
                IntegrationToken.organization_id == current_organization_id,
                IntegrationToken.expires_at < credential_cutoff,
                or_(
                    IntegrationToken.revoked_at.is_not(None),
                    IntegrationToken.expires_at < now,
                ),
            ),
        )
        totals["audit_logs"] += _execute_delete(
            db,
            delete(AuditLog).where(
                AuditLog.organization_id == current_organization_id,
                AuditLog.created_at < now - timedelta(days=policy.audit_log_days),
            ),
        )
        policy.last_run_at = now
        policy.updated_at = now

    db.flush()
    return {
        "organizations": processed,
        "skipped": skipped,
        "deleted": dict(sorted(totals.items())),
        "run_at": now,
    }


def delete_site_data(db: Session, site: Site) -> dict[str, int]:
    active_jobs = db.scalar(
        select(ScanJob.id).where(
            ScanJob.site_id == site.id,
            ScanJob.status.not_in(TERMINAL_JOB_STATUSES),
        ).limit(1)
    )
    if active_jobs is not None:
        raise ValueError("Cancel or complete active scan jobs before deleting this site")

    ids = {
        "sensors": _ids(db, Sensor, Sensor.site_id == site.id),
        "assets": _ids(db, Asset, Asset.site_id == site.id),
        "wifi_networks": _ids(db, WifiNetwork, WifiNetwork.site_id == site.id),
        "findings": _ids(db, Finding, Finding.site_id == site.id),
        "scan_runs": _ids(db, ScanRun, ScanRun.site_id == site.id),
        "scan_jobs": _ids(db, ScanJob, ScanJob.site_id == site.id),
        "scan_schedules": _ids(db, ScanSchedule, ScanSchedule.site_id == site.id),
        "baselines": _ids(db, BaselineRule, BaselineRule.site_id == site.id),
        "reports": _ids(db, Report, Report.site_id == site.id),
        "notification_endpoints": _ids(
            db, NotificationEndpoint, NotificationEndpoint.site_id == site.id
        ),
        "sensor_enrollments": _ids(
            db, SensorEnrollment, SensorEnrollment.site_id == site.id
        ),
    }
    ids["services"] = (
        _ids(db, Service, Service.asset_id.in_(ids["assets"]))
        if ids["assets"]
        else []
    )
    ids["asset_observations"] = _ids(
        db, AssetObservation, AssetObservation.site_id == site.id
    )
    ids["finding_notes"] = (
        _ids(db, FindingNote, FindingNote.finding_id.in_(ids["findings"]))
        if ids["findings"]
        else []
    )
    ids["notification_deliveries"] = list(
        db.scalars(
            select(NotificationDelivery.id).where(
                or_(
                    NotificationDelivery.site_id == site.id,
                    NotificationDelivery.endpoint_id.in_(ids["notification_endpoints"])
                    if ids["notification_endpoints"]
                    else False,
                )
            )
        ).all()
    )
    owned_resource_ids = {site.id}
    for values in ids.values():
        owned_resource_ids.update(values)

    counts: Counter[str] = Counter()
    counts["audit_logs"] += _execute_delete(
        db,
        delete(AuditLog).where(
            AuditLog.organization_id == site.organization_id,
            or_(
                AuditLog.resource_id.in_(owned_resource_ids),
                AuditLog.sensor_id.in_(ids["sensors"]) if ids["sensors"] else False,
            ),
        ),
    )
    for label, model in (
        ("finding_notes", FindingNote),
        ("findings", Finding),
        ("services", Service),
        ("asset_observations", AssetObservation),
        ("assets", Asset),
        ("wifi_networks", WifiNetwork),
        ("baselines", BaselineRule),
        ("reports", Report),
        ("scan_jobs", ScanJob),
        ("scan_schedules", ScanSchedule),
        ("scan_runs", ScanRun),
        ("notification_deliveries", NotificationDelivery),
        ("notification_endpoints", NotificationEndpoint),
        ("sensor_enrollments", SensorEnrollment),
        ("sensors", Sensor),
    ):
        if label == "notification_deliveries":
            condition = or_(
                NotificationDelivery.site_id == site.id,
                NotificationDelivery.endpoint_id.in_(ids["notification_endpoints"])
                if ids["notification_endpoints"]
                else False,
            )
        elif label in {"finding_notes", "services"}:
            condition = model.id.in_(ids[label])
        elif label == "notification_endpoints":
            condition = NotificationEndpoint.site_id == site.id
        elif label == "sensor_enrollments":
            condition = SensorEnrollment.site_id == site.id
        elif hasattr(model, "site_id"):
            condition = model.site_id == site.id
        else:
            condition = model.id.in_(ids[label])
        counts[label] += _execute_delete(db, delete(model).where(condition))

    counts["sites"] += _execute_delete(db, delete(Site).where(Site.id == site.id))
    db.flush()
    return dict(sorted(counts.items()))


def _ids(db: Session, model, condition) -> list[str]:
    return list(db.scalars(select(model.id).where(condition)).all())


def _execute_delete(db: Session, statement) -> int:
    result = db.execute(statement)
    return int(result.rowcount or 0)
