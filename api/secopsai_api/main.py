from __future__ import annotations

import secrets
import unicodedata
from contextlib import asynccontextmanager
from html import escape
from ipaddress import ip_address, ip_network
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from secopsai_api.ai import build_report
from secopsai_api import __version__
from secopsai_api.account_recovery import (
    attempt_account_access_delivery,
    consume_password_reset,
    process_due_account_access_deliveries,
    queue_password_reset,
    queue_user_invitation,
    validate_user_invitation,
    USER_INVITATION_PURPOSE,
)
from secopsai_api.audit import write_audit
from secopsai_api.baselines import (
    ALLOWED_FINDING_TYPES,
    apply_rule_to_existing_findings,
    default_finding_types,
    release_rule_findings,
)
from secopsai_api.config import get_settings
from secopsai_api.core_export import build_core_export
from secopsai_api.database import engine, get_db
from secopsai_api.detection import ingest_scan
from secopsai_api.models import (
    Asset,
    AccountAccessToken,
    AssetObservation,
    AuditLog,
    Base,
    BaselineRule,
    Finding,
    FindingNote,
    IntegrationToken,
    NotificationDelivery,
    NotificationEndpoint,
    Organization,
    OrganizationMembership,
    Report,
    ScanJob,
    ScanRun,
    ScanSchedule,
    Sensor,
    SensorEnrollment,
    Service,
    Site,
    User,
    WifiNetwork,
    utcnow,
)
from secopsai_api.notifications import attempt_delivery, notify_event, process_due_deliveries, test_notification
from secopsai_api.mfa import (
    begin_mfa_setup,
    create_mfa_challenge,
    decode_mfa_challenge,
    disable_mfa,
    enable_mfa,
    replace_recovery_codes,
    verify_mfa_code,
)
from secopsai_api.report_pdf import render_report_pdf
from secopsai_api.scheduling import compute_next_run_at, enqueue_due_schedules, normalize_frequency, pick_site_and_sensor
from secopsai_api.schemas import (
    AssetDetailOut,
    AssetTimelineEventOut,
    AssetOut,
    AuditLogOut,
    BaselineFromEntityRequest,
    BaselineRuleCreateRequest,
    BaselineRuleOut,
    BaselineRuleUpdateRequest,
    DashboardLoginRequest,
    DashboardSessionResponse,
    DashboardLoginResponse,
    DashboardUserLoginRequest,
    FindingDetailOut,
    FindingNoteCreateRequest,
    FindingNoteOut,
    FindingOut,
    HeartbeatIn,
    IntegrationTokenCreateRequest,
    IntegrationTokenCreateResponse,
    IntegrationTokenOut,
    IntegrationTokenRotateRequest,
    NotificationEndpointCreateRequest,
    NotificationDeliveryOut,
    NotificationEndpointOut,
    NotificationRunResponse,
    NotificationEndpointUpdateRequest,
    NotificationTestResponse,
    AccountAccessDeliveryOut,
    AccountAccessRunResponse,
    OrganizationCreateRequest,
    OrganizationOut,
    OrganizationUpdateRequest,
    OnboardingStatusOut,
    ReportOut,
    ScanIn,
    ScanIngestResponse,
    ScanJobCreateRequest,
    ScanJobFailRequest,
    ScanJobOut,
    ScanJobStartRequest,
    RunDueSchedulesResponse,
    ScanScheduleCreateRequest,
    ScanScheduleOut,
    ScanScheduleUpdateRequest,
    SensorRotateResponse,
    SensorUpdateRequest,
    SensorOut,
    SensorRegisterRequest,
    SensorRegisterResponse,
    SensorEnrollRequest,
    SensorEnrollmentCreateRequest,
    SensorEnrollmentCreateResponse,
    SensorEnrollmentOut,
    SiteCreateRequest,
    SiteOut,
    SiteUpdateRequest,
    AuthMeOut,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    MfaChallengeRequest,
    MfaCodeRequest,
    MfaPasswordRequest,
    MfaProtectedActionRequest,
    MfaRecoveryCodesOut,
    MfaSetupOut,
    UserCreateRequest,
    UserInvitationAcceptRequest,
    UserInvitationCreateRequest,
    UserInvitationOut,
    UserOut,
    UserUpdateRequest,
    WorkspaceSwitchRequest,
    WifiNetworkOut,
)
from secopsai_api.security import (
    authenticate_sensor,
    constant_time_equals,
    create_dashboard_session,
    get_dashboard_auth_context,
    generate_sensor_token,
    generate_integration_token,
    hash_password,
    hash_secret,
    DUMMY_PASSWORD_HASH,
    require_admin,
    require_core_export_access,
    require_integration_token_access,
    require_operations_read_access,
    require_operator,
    require_sensor_for_path,
    verify_password,
)
from secopsai_api.tenancy import (
    count_active_workspace_admins,
    ensure_default_membership,
    ensure_default_organization,
    ensure_default_tenant_state,
    membership_for_user,
    organization_id_from_context,
    require_active_organization,
    site_for_organization,
    touch_membership,
    unique_slug,
)
from secopsai_api.splunk import export_finding, export_report


settings = get_settings()
PRIVATE_SCAN_RANGES = tuple(
    ip_network(cidr) for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
TERMINAL_SCAN_JOB_STATUSES = {"completed", "failed", "canceled"}
SENSOR_OFFLINE_AFTER = timedelta(minutes=3)
STALE_SCAN_JOB_AFTER = timedelta(minutes=15)
ALLOWED_INTEGRATION_TOKEN_SCOPES = {"core:export", "operations:read"}

def bootstrap_dashboard_admin(db: Session) -> None:
    ensure_default_organization(db)
    if not settings.dashboard_admin_email or not settings.dashboard_admin_password:
        return
    email = settings.dashboard_admin_email.strip().lower()
    if not email:
        return
    if len(settings.dashboard_admin_password) < 12:
        raise RuntimeError("SECOPSAI_DASHBOARD_ADMIN_PASSWORD must be at least 12 characters")
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is not None:
        return
    user = User(
        email=email,
        password_hash=hash_password(settings.dashboard_admin_password),
        password_ready=True,
        role="admin",
        active=True,
    )
    db.add(user)
    db.flush()
    membership = ensure_default_membership(db, user)
    membership.role = "admin"
    membership.active = True
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        ensure_default_organization(db)
        db.commit()
        bootstrap_dashboard_admin(db)
    yield


app = FastAPI(title="SecOpsAI Edge API", version=settings.release_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {
        "status": "ok",
        "version": settings.release_version,
        "commit": settings.release_commit[:12],
    }


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready", "reason": "database_unavailable"})
    if revision != settings.expected_schema_revision:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": "schema_out_of_date",
                "schema_revision": revision,
                "expected_revision": settings.expected_schema_revision,
            },
        )
    return JSONResponse(
        content={
            "status": "ready",
            "schema_revision": revision,
            "version": settings.release_version,
        }
    )


@app.get("/api/v1/system/status")
def system_status(
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    return {
        "status": "ready" if revision == settings.expected_schema_revision else "degraded",
        "environment": settings.environment,
        "version": settings.release_version,
        "commit": settings.release_commit,
        "schema_revision": revision,
        "expected_schema_revision": settings.expected_schema_revision,
        "ai_provider": settings.ai_provider,
        "organization_id": organization_id_from_context(auth_context),
        "server_time": utcnow().isoformat(),
    }


def normalize_scan_job_target(target_cidr: str) -> str:
    try:
        network = ip_network(target_cidr, strict=False)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CIDR target",
        ) from exc

    if network.version != 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only IPv4 CIDRs are supported")
    if not any(network.subnet_of(allowed) for allowed in PRIVATE_SCAN_RANGES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only RFC1918 private CIDRs are allowed for remote jobs",
        )
    if network.prefixlen < 24 or network.num_addresses > 256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Remote scan jobs are limited to /24 or narrower CIDRs",
        )
    return str(network)


def get_sensor_job(db: Session, sensor: Sensor, job_id: str) -> ScanJob:
    job = db.get(ScanJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan job not found")
    if job.sensor_id != sensor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Scan job belongs to a different sensor")
    return job


def get_sensor_for_organization(db: Session, sensor_id: str, organization_id: str) -> Sensor:
    sensor = db.scalar(
        select(Sensor)
        .join(Site, Site.id == Sensor.site_id)
        .where(Sensor.id == sensor_id, Site.organization_id == organization_id)
    )
    if sensor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    return sensor


def get_scan_job_for_organization(db: Session, job_id: str, organization_id: str) -> ScanJob:
    job = db.scalar(
        select(ScanJob)
        .join(Site, Site.id == ScanJob.site_id)
        .where(ScanJob.id == job_id, Site.organization_id == organization_id)
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan job not found")
    return job


def get_scan_schedule_for_organization(
    db: Session, schedule_id: str, organization_id: str
) -> ScanSchedule:
    schedule = db.scalar(
        select(ScanSchedule)
        .join(Site, Site.id == ScanSchedule.site_id)
        .where(ScanSchedule.id == schedule_id, Site.organization_id == organization_id)
    )
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan schedule not found")
    return schedule


def is_stale(timestamp, max_age: timedelta) -> bool:
    if timestamp is None:
        return True
    now = utcnow()
    if timestamp.tzinfo is None:
        now = now.replace(tzinfo=None)
    return now - timestamp > max_age


def recover_stale_scan_jobs(db: Session, sensor_id: str | None = None) -> None:
    query = select(ScanJob).where(ScanJob.status.in_(["claimed", "running"]))
    if sensor_id:
        query = query.where(ScanJob.sensor_id == sensor_id)
    now = utcnow()
    changed = False
    for job in db.scalars(query).all():
        if is_stale(job.updated_at, STALE_SCAN_JOB_AFTER):
            job.status = "queued"
            job.claimed_at = None
            job.started_at = None
            job.error_message = None
            job.updated_at = now
            changed = True
    if changed:
        db.flush()


def sensor_connection_state(sensor: Sensor) -> str:
    if is_stale(sensor.last_seen_at, SENSOR_OFFLINE_AFTER):
        return "offline"
    return "online"


def current_sensor_job(db: Session, sensor: Sensor) -> ScanJob | None:
    return db.scalar(
        select(ScanJob)
        .where(ScanJob.sensor_id == sensor.id, ScanJob.status.in_(["claimed", "running"]))
        .order_by(ScanJob.updated_at.desc())
    )


def get_site_or_404(db: Session, site_id: str, organization_id: str | None = None) -> Site:
    site = (
        site_for_organization(db, site_id, organization_id)
        if organization_id
        else db.get(Site, site_id)
    )
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


def get_asset_or_404(db: Session, asset_id: str, organization_id: str | None = None) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    if organization_id:
        get_site_or_404(db, asset.site_id, organization_id)
    return asset


def get_service_or_404(db: Session, service_id: str, organization_id: str | None = None) -> Service:
    service = db.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    if organization_id:
        get_asset_or_404(db, service.asset_id, organization_id)
    return service


def get_wifi_or_404(db: Session, wifi_id: str, organization_id: str | None = None) -> WifiNetwork:
    wifi = db.get(WifiNetwork, wifi_id)
    if wifi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wi-Fi network not found")
    if organization_id:
        get_site_or_404(db, wifi.site_id, organization_id)
    return wifi


def get_baseline_or_404(db: Session, baseline_id: str, organization_id: str | None = None) -> BaselineRule:
    rule = db.get(BaselineRule, baseline_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Baseline rule not found")
    if organization_id:
        get_site_or_404(db, rule.site_id, organization_id)
    return rule


def create_or_update_baseline(
    db: Session,
    *,
    site_id: str,
    kind: str,
    matcher: dict[str, object],
    finding_types: list[str],
    reason: str | None,
    created_by: str,
    expires_at: datetime | None,
) -> tuple[BaselineRule, int]:
    get_site_or_404(db, site_id)
    normalized_matcher = {
        key: value for key, value in matcher.items() if value is not None and value != ""
    }
    if not normalized_matcher:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Baseline matcher cannot be empty")
    required_identity = {
        "asset": {"asset_id", "ip_address", "mac_address"},
        "service": {"service_id", "asset_id", "ip_address", "mac_address"},
        "wifi": {"wifi_network_id", "bssid"},
    }[kind]
    if not required_identity.intersection(normalized_matcher):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{kind} baseline requires a stable entity identifier",
        )
    if kind == "service" and "port" not in normalized_matcher:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Service baseline requires a port")
    unsupported = set(finding_types) - ALLOWED_FINDING_TYPES[kind]
    if unsupported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported finding types for {kind}: {', '.join(sorted(unsupported))}",
        )

    existing = db.scalar(
        select(BaselineRule).where(
            BaselineRule.site_id == site_id,
            BaselineRule.kind == kind,
            BaselineRule.status == "active",
            BaselineRule.matcher == normalized_matcher,
        )
    )
    if existing:
        existing.finding_types = list(dict.fromkeys(finding_types))
        existing.reason = reason.strip() if reason else existing.reason
        existing.created_by = created_by.strip()
        existing.expires_at = expires_at
        existing.updated_at = utcnow()
        rule = existing
    else:
        rule = BaselineRule(
            site_id=site_id,
            kind=kind,
            matcher=normalized_matcher,
            finding_types=list(dict.fromkeys(finding_types)),
            reason=reason.strip() if reason else None,
            created_by=created_by.strip(),
            expires_at=expires_at,
        )
        db.add(rule)
        db.flush()
    changed = apply_rule_to_existing_findings(db, rule)
    write_audit(
        db,
        "baseline.saved",
        resource_type="baseline",
        resource_id=rule.id,
        details={"kind": kind, "finding_types": rule.finding_types, "findings_acknowledged": changed},
    )
    return rule, changed


def get_finding_or_404(db: Session, finding_id: str, organization_id: str | None = None) -> Finding:
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    if organization_id:
        get_site_or_404(db, finding.site_id, organization_id)
    return finding


def get_report_or_404(db: Session, report_id: str, organization_id: str | None = None) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if organization_id:
        get_site_or_404(db, report.site_id, organization_id)
    return report


def report_export_filename(report: Report, extension: str = "html") -> str:
    ascii_title = unicodedata.normalize("NFKD", report.title).encode("ascii", "ignore").decode("ascii")
    slug = "".join(char.lower() if char.isalnum() else "-" for char in ascii_title)
    slug = "-".join(part for part in slug.split("-") if part)
    return f"{slug or 'secopsai-edge-report'}.{extension}"


def render_report_html(report: Report, site: Site | None) -> str:
    content = report.content if isinstance(report.content, dict) else {}
    findings = content.get("findings", [])
    recommended_actions = content.get("recommended_actions", [])
    provider = str(content.get("provider", "unknown"))
    model = str(content.get("model", "n/a"))
    site_name = site.name if site else "Unknown site"
    generated_at = report.created_at.strftime("%Y-%m-%d %H:%M UTC")

    def finding_card(item: object) -> str:
        finding = item if isinstance(item, dict) else {}
        severity = escape(str(finding.get("severity", "info")))
        title = escape(str(finding.get("title", "Untitled finding")))
        summary = escape(str(finding.get("summary", "No summary provided.")))
        status_value = escape(str(finding.get("status", "open")))
        finding_type = escape(str(finding.get("type", "finding")))
        return (
            '<article class="finding">'
            f'<div><span class="severity">{severity}</span><span class="muted">{finding_type} · {status_value}</span></div>'
            f"<h3>{title}</h3><p>{summary}</p>"
            "</article>"
        )

    actions_html = "".join(f"<li>{escape(str(action))}</li>" for action in recommended_actions)
    findings_html = "".join(finding_card(item) for item in findings)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(report.title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1f2933;
      --muted: #52606d;
      --line: #d9ded7;
      --paper: #f6f8f5;
      --sea: #0f766e;
      --danger: #b42318;
      --amber: #b54708;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: #fff; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 40px 28px 56px; }}
    header {{ border-bottom: 1px solid var(--line); padding-bottom: 24px; margin-bottom: 28px; }}
    .eyebrow {{ color: var(--sea); font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }}
    h1 {{ margin: 10px 0 12px; font-size: 32px; line-height: 1.2; }}
    h2 {{ margin: 28px 0 12px; font-size: 20px; }}
    h3 {{ margin: 12px 0 6px; font-size: 16px; }}
    p {{ line-height: 1.65; }}
    .summary {{ max-width: 820px; font-size: 15px; color: #334155; }}
    .meta {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 20px; }}
    .box {{ border: 1px solid var(--line); border-radius: 8px; background: var(--paper); padding: 12px; }}
    .label {{ color: var(--muted); font-size: 12px; }}
    .value {{ margin-top: 4px; font-weight: 700; }}
    .severity {{ display: inline-flex; border: 1px solid var(--line); border-radius: 4px; padding: 3px 8px; margin-right: 8px; font-size: 12px; font-weight: 800; text-transform: uppercase; }}
    .muted {{ color: var(--muted); font-size: 13px; }}
    ol {{ padding-left: 22px; }}
    li {{ margin: 8px 0; line-height: 1.55; }}
    .finding {{ border: 1px solid var(--line); border-radius: 8px; padding: 14px; margin: 12px 0; break-inside: avoid; }}
    footer {{ margin-top: 36px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: 12px; }}
    @media print {{
      main {{ max-width: none; padding: 24px; }}
      .meta {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="eyebrow">SecOpsAI Edge Report</div>
      <h1>{escape(report.title)}</h1>
      <p class="summary">{escape(report.summary)}</p>
      <section class="meta">
        <div class="box"><div class="label">Site</div><div class="value">{escape(site_name)}</div></div>
        <div class="box"><div class="label">Generated</div><div class="value">{escape(generated_at)}</div></div>
        <div class="box"><div class="label">Risk</div><div class="value">{escape(report.risk_level.upper())}</div></div>
        <div class="box"><div class="label">AI Provider</div><div class="value">{escape(provider)} / {escape(model)}</div></div>
      </section>
    </header>
    <section>
      <h2>Recommended Actions</h2>
      <ol>{actions_html or "<li>No recommended actions were included.</li>"}</ol>
    </section>
    <section>
      <h2>Findings Included</h2>
      {findings_html or "<p>No active findings were included.</p>"}
    </section>
    <footer>
      Raw Nmap output, packet captures, and full scan logs are not included in this report.
    </footer>
  </main>
</body>
</html>"""


def build_asset_timeline(
    asset: Asset,
    observations: list[AssetObservation],
    findings: list[Finding],
) -> list[AssetTimelineEventOut]:
    events: list[AssetTimelineEventOut] = [
        AssetTimelineEventOut(
            id=f"asset-first-seen-{asset.id}",
            kind="asset_first_seen",
            title="Asset first observed",
            summary=f"{asset.hostname or asset.ip_address} first appeared in the site inventory.",
            occurred_at=asset.first_seen_at,
            metadata={"ip_address": asset.ip_address, "vendor": asset.vendor, "device_type": asset.device_type},
        )
    ]

    if asset.status == "missing":
        events.append(
            AssetTimelineEventOut(
                id=f"asset-missing-{asset.id}",
                kind="asset_missing",
                title="Asset currently missing",
                summary=f"{asset.hostname or asset.ip_address} has not been observed in the latest scan window.",
                occurred_at=asset.last_seen_at,
                severity="medium",
                metadata={"ip_address": asset.ip_address},
            )
        )

    for service in sorted(asset.services or [], key=lambda item: (item.first_seen_at, item.port)):
        events.append(
            AssetTimelineEventOut(
                id=f"service-{service.id}",
                kind="service_observed",
                title="Service observed",
                summary=f"{service.protocol}/{service.port} {service.name or ''}".strip(),
                occurred_at=service.first_seen_at,
                severity="medium" if service.state == "open" else "info",
                metadata={
                    "port": service.port,
                    "protocol": service.protocol,
                    "state": service.state,
                    "product": service.product,
                    "version": service.version,
                },
            )
        )

    for observation in observations:
        events.append(
            AssetTimelineEventOut(
                id=f"observation-{observation.id}",
                kind="asset_observed",
                title="Asset observed",
                summary=f"Observed from {observation.raw_source or 'sensor scan'} with hostname {observation.hostname or 'unknown'}.",
                occurred_at=observation.observed_at,
                metadata={
                    "sensor_id": observation.sensor_id,
                    "scan_id": observation.scan_id,
                    "vendor": observation.vendor,
                    "os_guess": observation.os_guess,
                },
            )
        )

    for finding in findings:
        events.append(
            AssetTimelineEventOut(
                id=f"finding-{finding.id}",
                kind="finding_created",
                title=finding.title,
                summary=finding.summary,
                occurred_at=finding.created_at,
                severity=finding.severity,
                metadata={"finding_id": finding.id, "type": finding.type, "status": finding.status},
            )
        )

    return sorted(events, key=lambda event: event.occurred_at, reverse=True)


def finding_notification_payload(finding: Finding) -> dict[str, object]:
    return {
        "id": finding.id,
        "title": finding.title,
        "summary": finding.summary,
        "severity": finding.severity,
        "type": finding.type,
        "status": finding.status,
        "evidence": finding.evidence,
    }


def sensor_out(db: Session, sensor: Sensor) -> SensorOut:
    return SensorOut(
        id=sensor.id,
        site_id=sensor.site_id,
        site_name=sensor.site.name,
        name=sensor.name,
        hostname=sensor.hostname,
        status=sensor.status,
        connection_state="disabled" if sensor.disabled_at else sensor_connection_state(sensor),
        version=sensor.version,
        os_name=sensor.os_name,
        worker_state=sensor.worker_state,
        current_job_id=sensor.current_job_id,
        last_error=sensor.last_error,
        disabled_at=sensor.disabled_at,
        created_at=sensor.created_at,
        last_seen_at=sensor.last_seen_at,
        current_job=current_sensor_job(db, sensor),
    )


def sensor_enrollment_out(db: Session, enrollment: SensorEnrollment) -> SensorEnrollmentOut:
    site = db.get(Site, enrollment.site_id)
    now = utcnow()
    expires_at = enrollment.expires_at
    if expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)
    if enrollment.revoked_at is not None:
        state = "revoked"
    elif enrollment.used_at is not None:
        state = "used"
    elif expires_at <= now:
        state = "expired"
    else:
        state = "active"
    return SensorEnrollmentOut(
        id=enrollment.id,
        organization_id=enrollment.organization_id,
        site_id=enrollment.site_id,
        site_name=site.name if site else "Unknown site",
        label=enrollment.label,
        state=state,
        expires_at=enrollment.expires_at,
        used_at=enrollment.used_at,
        revoked_at=enrollment.revoked_at,
        created_at=enrollment.created_at,
    )


def integration_token_out(token: IntegrationToken) -> IntegrationTokenOut:
    now = utcnow()
    comparison_now = now if token.expires_at.tzinfo is not None else now.replace(tzinfo=None)
    remaining_seconds = (token.expires_at - comparison_now).total_seconds()
    expires_in_days = max(0, int((remaining_seconds + 86_399) // 86_400))
    if token.revoked_at is not None:
        state = "revoked"
    elif token.expires_at <= comparison_now:
        state = "expired"
    else:
        state = "active"
    return IntegrationTokenOut(
        id=token.id,
        organization_id=token.organization_id,
        name=token.name,
        scopes=list(token.scopes or []),
        state=state,
        expires_at=token.expires_at,
        expires_in_days=expires_in_days,
        rotation_recommended=state == "active" and expires_in_days <= 14,
        last_used_at=token.last_used_at,
        revoked_at=token.revoked_at,
        created_at=token.created_at,
    )


def cidr_for_asset(asset: Asset) -> str:
    ip = ip_address(asset.ip_address)
    if ip.version != 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only IPv4 assets can be rescanned")
    return str(ip_network(f"{asset.ip_address}/24", strict=False))


@app.post("/api/v1/auth/session", response_model=DashboardSessionResponse)
def create_session(payload: DashboardLoginRequest) -> DashboardSessionResponse:
    if not constant_time_equals(payload.admin_token, settings.admin_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
    return DashboardSessionResponse(
        access_token=create_dashboard_session(subject="admin-token", role="admin"),
        expires_in=settings.dashboard_session_ttl_seconds,
    )


@app.post("/api/v1/auth/login", response_model=DashboardLoginResponse)
def login_dashboard_user(payload: DashboardUserLoginRequest, db: Session = Depends(get_db)) -> DashboardLoginResponse:
    email = payload.email.strip().lower()
    user = db.scalar(
        select(User).where(func.lower(User.email) == email).with_for_update()
    )
    if user is None:
        verify_password(payload.password, DUMMY_PASSWORD_HASH)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid email or password")
    if account_is_locked(user):
        write_audit(db, "auth.login_blocked", user_id=user.id, resource_type="user", resource_id=user.id)
        db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Login temporarily unavailable")
    password_valid = verify_password(payload.password, user.password_hash)
    if not password_valid or not user.active or not user.password_ready:
        user.failed_login_count += 1
        action = "auth.login_failed"
        if user.failed_login_count >= settings.login_max_attempts:
            user.locked_until = utcnow() + timedelta(seconds=settings.login_lockout_seconds)
            action = "auth.login_locked"
        write_audit(db, action, user_id=user.id, resource_type="user", resource_id=user.id)
        db.commit()
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if action == "auth.login_locked"
            else status.HTTP_403_FORBIDDEN
        )
        detail = "Login temporarily unavailable" if status_code == 429 else "Invalid email or password"
        raise HTTPException(status_code=status_code, detail=detail)

    membership = membership_for_user(db, user.id)
    if membership is None:
        existing_membership = db.scalar(
            select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
        )
        if existing_membership is not None:
            write_audit(db, "auth.login_failed", user_id=user.id, resource_type="user", resource_id=user.id)
            db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid email or password")
        membership = ensure_default_membership(db, user)

    if user.mfa_enabled_at is not None:
        write_audit(
            db,
            "auth.mfa_challenge_issued",
            user_id=user.id,
            organization_id=membership.organization_id,
            resource_type="user",
            resource_id=user.id,
        )
        db.commit()
        return DashboardLoginResponse(
            expires_in=settings.mfa_challenge_ttl_seconds,
            user=user_out(user, membership.role, membership.active),
            mfa_required=True,
            mfa_challenge=create_mfa_challenge(user, membership.organization_id, settings),
        )

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = utcnow()
    write_audit(
        db,
        "auth.login",
        user_id=user.id,
        organization_id=membership.organization_id,
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return DashboardLoginResponse(
        access_token=create_dashboard_session(
            subject=user.email,
            role=membership.role,
            user_id=user.id,
            session_version=user.session_version,
            organization_id=membership.organization_id,
        ),
        expires_in=settings.dashboard_session_ttl_seconds,
        user=user_out(user, membership.role, membership.active),
    )


@app.post("/api/v1/auth/mfa/verify", response_model=DashboardSessionResponse)
def verify_dashboard_mfa(
    payload: MfaChallengeRequest,
    db: Session = Depends(get_db),
) -> DashboardSessionResponse:
    challenge = decode_mfa_challenge(payload.challenge, settings)
    if challenge is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MFA challenge is invalid or expired")
    user = db.scalar(
        select(User).where(User.id == str(challenge["uid"])).with_for_update()
    )
    organization_id = str(challenge["org"])
    membership = membership_for_user(db, user.id, organization_id) if user else None
    if (
        user is None
        or not user.active
        or not user.password_ready
        or membership is None
        or int(challenge.get("ver", 0)) != user.session_version
        or user.mfa_enabled_at is None
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MFA challenge is invalid or expired")
    if account_is_locked(user):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Login temporarily unavailable")
    if not verify_mfa_code(db, user, payload.code, settings):
        user.failed_login_count += 1
        action = "auth.mfa_failed"
        if user.failed_login_count >= settings.login_max_attempts:
            user.locked_until = utcnow() + timedelta(seconds=settings.login_lockout_seconds)
            action = "auth.login_locked"
        write_audit(
            db,
            action,
            user_id=user.id,
            organization_id=membership.organization_id,
            resource_type="user",
            resource_id=user.id,
        )
        db.commit()
        status_code = status.HTTP_429_TOO_MANY_REQUESTS if action == "auth.login_locked" else status.HTTP_403_FORBIDDEN
        detail = "Login temporarily unavailable" if status_code == 429 else "Invalid authentication code"
        raise HTTPException(status_code=status_code, detail=detail)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = utcnow()
    write_audit(
        db,
        "auth.mfa_verified",
        user_id=user.id,
        organization_id=membership.organization_id,
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return DashboardSessionResponse(
        access_token=create_dashboard_session(
            subject=user.email,
            role=membership.role,
            user_id=user.id,
            session_version=user.session_version,
            organization_id=membership.organization_id,
        ),
        expires_in=settings.dashboard_session_ttl_seconds,
        user=user_out(user, membership.role, membership.active),
    )


@app.post("/api/v1/auth/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_dashboard_password_reset(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email, User.active.is_(True)))
    if user is not None:
        reset = queue_password_reset(db, user, settings)
        membership = membership_for_user(db, user.id)
        write_audit(
            db,
            "auth.password_reset_requested" if reset is not None else "auth.password_reset_throttled",
            user_id=user.id,
            organization_id=membership.organization_id if membership else None,
            resource_type="user",
            resource_id=user.id,
        )
        db.commit()
    else:
        # Keep the response and cryptographic work independent of account
        # existence; public callers never learn whether an email is registered.
        hash_secret(f"password-reset:{email}")
    return {"status": "accepted"}


@app.post("/api/v1/auth/password-reset/confirm")
def confirm_dashboard_password_reset(
    payload: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = consume_password_reset(db, payload.token, payload.new_password, settings=settings)
    if user is None:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link is invalid or expired",
        )
    membership = membership_for_user(db, user.id)
    write_audit(
        db,
        "auth.password_reset_completed",
        user_id=user.id,
        organization_id=membership.organization_id if membership else None,
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    return {"status": "password_reset"}


def account_is_locked(user: User) -> bool:
    if user.locked_until is None:
        return False
    now = utcnow()
    if user.locked_until.tzinfo is None:
        now = now.replace(tzinfo=None)
    return user.locked_until > now


def organization_out(organization: Organization, role: str) -> OrganizationOut:
    return OrganizationOut(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        active=organization.active,
        role=role,
        created_at=organization.created_at,
    )


def user_out(user: User, role: str, active: bool) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        role=role,
        active=active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        password_changed_at=user.password_changed_at,
        mfa_enabled=user.mfa_enabled_at is not None,
    )


def organizations_for_context(db: Session, auth_context: dict) -> list[OrganizationOut]:
    if auth_context.get("legacy"):
        organization = ensure_default_tenant_state(db)
        return [organization_out(organization, "admin")]
    user_id = auth_context.get("uid")
    if not user_id:
        organization = ensure_default_tenant_state(db)
        return [organization_out(organization, str(auth_context.get("role") or "viewer"))]
    rows = db.execute(
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
        .where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.active.is_(True),
            Organization.active.is_(True),
        )
        .order_by(Organization.name.asc())
    ).all()
    return [organization_out(organization, role) for organization, role in rows]


@app.get("/api/v1/auth/me", response_model=AuthMeOut)
def auth_me(
    auth_context: dict = Depends(get_dashboard_auth_context),
    db: Session = Depends(get_db),
) -> AuthMeOut:
    user = db.get(User, auth_context.get("uid")) if auth_context.get("uid") else None
    serialized_user = (
        user_out(user, str(auth_context.get("role") or user.role), True) if user else None
    )
    return AuthMeOut(
        subject=str(auth_context.get("sub") or "dashboard"),
        role=str(auth_context.get("role") or "admin"),
        organization_id=organization_id_from_context(auth_context),
        organizations=organizations_for_context(db, auth_context),
        user=serialized_user,
    )


@app.post("/api/v1/auth/workspace", response_model=DashboardSessionResponse)
def switch_workspace(
    payload: WorkspaceSwitchRequest,
    auth_context: dict = Depends(get_dashboard_auth_context),
    db: Session = Depends(get_db),
) -> DashboardSessionResponse:
    user = db.get(User, auth_context.get("uid")) if auth_context.get("uid") else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User login required")
    membership = membership_for_user(db, user.id, payload.organization_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    write_audit(
        db,
        "auth.workspace_switched",
        user_id=user.id,
        organization_id=membership.organization_id,
        resource_type="organization",
        resource_id=membership.organization_id,
    )
    db.commit()
    return DashboardSessionResponse(
        access_token=create_dashboard_session(
            subject=user.email,
            role=membership.role,
            user_id=user.id,
            session_version=user.session_version,
            organization_id=membership.organization_id,
        ),
        expires_in=settings.dashboard_session_ttl_seconds,
        user=user_out(user, membership.role, membership.active),
    )


@app.post("/api/v1/auth/logout")
def logout_dashboard_user(
    auth_context: dict = Depends(get_dashboard_auth_context),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = (
        db.scalar(select(User).where(User.id == auth_context["uid"]).with_for_update())
        if auth_context.get("uid")
        else None
    )
    if user is not None:
        user.session_version += 1
        write_audit(
            db,
            "auth.logout",
            user_id=user.id,
            organization_id=organization_id_from_context(auth_context),
            resource_type="user",
            resource_id=user.id,
        )
        db.commit()
    return {"status": "logged_out"}


@app.post("/api/v1/auth/change-password")
def change_dashboard_password(
    payload: PasswordChangeRequest,
    auth_context: dict = Depends(get_dashboard_auth_context),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = (
        db.scalar(select(User).where(User.id == auth_context["uid"]).with_for_update())
        if auth_context.get("uid")
        else None
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User login required")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect")
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")
    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = utcnow()
    user.session_version += 1
    write_audit(
        db,
        "auth.password_changed",
        user_id=user.id,
        organization_id=organization_id_from_context(auth_context),
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    return {"status": "password_changed"}


@app.post("/api/v1/auth/mfa/setup", response_model=MfaSetupOut)
def setup_dashboard_mfa(
    payload: MfaPasswordRequest,
    auth_context: dict = Depends(get_dashboard_auth_context),
    db: Session = Depends(get_db),
) -> MfaSetupOut:
    user = (
        db.scalar(select(User).where(User.id == auth_context["uid"]).with_for_update())
        if auth_context.get("uid")
        else None
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User login required")
    if user.mfa_enabled_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Disable existing MFA before enrolling a replacement authenticator",
        )
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect")
    secret, uri = begin_mfa_setup(user, settings)
    write_audit(
        db,
        "auth.mfa_setup_started",
        user_id=user.id,
        organization_id=organization_id_from_context(auth_context),
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    return MfaSetupOut(
        secret=secret,
        provisioning_uri=uri,
        expires_at=user.mfa_pending_expires_at,
    )


@app.post("/api/v1/auth/mfa/enable", response_model=MfaRecoveryCodesOut)
def enable_dashboard_mfa(
    payload: MfaCodeRequest,
    auth_context: dict = Depends(get_dashboard_auth_context),
    db: Session = Depends(get_db),
) -> MfaRecoveryCodesOut:
    user = (
        db.scalar(select(User).where(User.id == auth_context["uid"]).with_for_update())
        if auth_context.get("uid")
        else None
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User login required")
    recovery_codes = enable_mfa(db, user, payload.code, settings)
    if recovery_codes is None:
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authentication code is invalid or setup expired")
    write_audit(
        db,
        "auth.mfa_enabled",
        user_id=user.id,
        organization_id=organization_id_from_context(auth_context),
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    return MfaRecoveryCodesOut(recovery_codes=recovery_codes)


@app.post("/api/v1/auth/mfa/recovery-codes", response_model=MfaRecoveryCodesOut)
def regenerate_dashboard_mfa_recovery_codes(
    payload: MfaProtectedActionRequest,
    auth_context: dict = Depends(get_dashboard_auth_context),
    db: Session = Depends(get_db),
) -> MfaRecoveryCodesOut:
    user = (
        db.scalar(select(User).where(User.id == auth_context["uid"]).with_for_update())
        if auth_context.get("uid")
        else None
    )
    if user is None or user.mfa_enabled_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA is not enabled")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect")
    if not verify_mfa_code(db, user, payload.code, settings):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authentication code")
    recovery_codes = replace_recovery_codes(db, user, settings)
    write_audit(
        db,
        "auth.mfa_recovery_codes_regenerated",
        user_id=user.id,
        organization_id=organization_id_from_context(auth_context),
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    return MfaRecoveryCodesOut(recovery_codes=recovery_codes)


@app.post("/api/v1/auth/mfa/disable")
def disable_dashboard_mfa(
    payload: MfaProtectedActionRequest,
    auth_context: dict = Depends(get_dashboard_auth_context),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = (
        db.scalar(select(User).where(User.id == auth_context["uid"]).with_for_update())
        if auth_context.get("uid")
        else None
    )
    if user is None or user.mfa_enabled_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA is not enabled")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect")
    if not verify_mfa_code(db, user, payload.code, settings):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authentication code")
    disable_mfa(db, user)
    write_audit(
        db,
        "auth.mfa_disabled",
        user_id=user.id,
        organization_id=organization_id_from_context(auth_context),
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    return {"status": "mfa_disabled"}


@app.get("/api/v1/organizations", response_model=list[OrganizationOut])
def list_organizations(
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> list[OrganizationOut]:
    return organizations_for_context(db, auth_context)


@app.post("/api/v1/organizations", response_model=OrganizationOut)
def create_organization(
    payload: OrganizationCreateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OrganizationOut:
    if auth_context.get("legacy") or auth_context.get("role") != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner user login required")
    name = payload.name.strip()
    organization = Organization(name=name, slug=unique_slug(db, name), active=True)
    membership = OrganizationMembership(
        organization=organization,
        user_id=str(auth_context["uid"]),
        role="owner",
        active=True,
    )
    db.add_all([organization, membership])
    db.flush()
    write_audit(
        db,
        "organization.created",
        user_id=str(auth_context["uid"]),
        organization_id=organization.id,
        resource_type="organization",
        resource_id=organization.id,
        details={"name": organization.name, "slug": organization.slug},
    )
    db.commit()
    db.refresh(organization)
    return organization_out(organization, "owner")


@app.patch("/api/v1/organizations/{organization_id}", response_model=OrganizationOut)
def update_organization(
    organization_id: str,
    payload: OrganizationUpdateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OrganizationOut:
    current_id = organization_id_from_context(auth_context)
    if organization_id != current_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if auth_context.get("legacy") or auth_context.get("role") != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required")
    organization = require_active_organization(db, current_id)
    if payload.name is not None:
        organization.name = payload.name.strip()
    organization.updated_at = utcnow()
    write_audit(
        db,
        "organization.updated",
        user_id=str(auth_context["uid"]),
        organization_id=organization.id,
        resource_type="organization",
        resource_id=organization.id,
        details={"name": organization.name},
    )
    db.commit()
    db.refresh(organization)
    return organization_out(organization, str(auth_context["role"]))


@app.get("/api/v1/users", response_model=list[UserOut])
def list_users(
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    organization_id = organization_id_from_context(auth_context)
    rows = db.execute(
        select(User, OrganizationMembership)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .where(OrganizationMembership.organization_id == organization_id)
        .order_by(User.created_at.asc())
    ).all()
    return [user_out(user, membership.role, membership.active) for user, membership in rows]


def user_invitation_out(row: AccountAccessToken, email: str) -> UserInvitationOut:
    now = utcnow()
    comparison_now = now if row.expires_at.tzinfo else now.replace(tzinfo=None)
    if row.delivery_detail == "Invitation accepted":
        state = "accepted"
    elif row.delivery_detail == "Invitation revoked":
        state = "revoked"
    elif row.expires_at <= comparison_now:
        state = "expired"
    elif row.used_at is not None:
        state = "closed"
    else:
        state = "pending"
    return UserInvitationOut(
        id=row.id,
        user_id=row.user_id,
        organization_id=str(row.organization_id),
        email=email,
        role=str((row.context or {}).get("role") or "viewer"),
        state=state,
        delivery_status=row.delivery_status,
        expires_at=row.expires_at,
        created_at=row.created_at,
    )


@app.get("/api/v1/user-invitations", response_model=list[UserInvitationOut])
def list_user_invitations(
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[UserInvitationOut]:
    organization_id = organization_id_from_context(auth_context)
    rows = db.execute(
        select(AccountAccessToken, User.email)
        .join(User, User.id == AccountAccessToken.user_id)
        .where(
            AccountAccessToken.organization_id == organization_id,
            AccountAccessToken.purpose == USER_INVITATION_PURPOSE,
        )
        .order_by(AccountAccessToken.created_at.desc())
    ).all()
    return [user_invitation_out(row, email) for row, email in rows]


@app.post("/api/v1/user-invitations", response_model=UserInvitationOut)
def create_user_invitation(
    payload: UserInvitationCreateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserInvitationOut:
    organization_id = organization_id_from_context(auth_context)
    if payload.role == "owner" and auth_context.get("role") != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required")
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(48)),
            password_ready=False,
            role=payload.role,
            active=False,
        )
        db.add(user)
        db.flush()
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user.id,
        )
    )
    if membership is not None and membership.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already belongs to this workspace")
    invitation = queue_user_invitation(
        db,
        user,
        organization_id,
        payload.role,
        new_user=not user.password_ready,
        settings=settings,
    )
    write_audit(
        db,
        "user.invited",
        user_id=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        organization_id=organization_id,
        resource_type="user_invitation",
        resource_id=invitation.id,
        details={"email": email, "role": payload.role},
    )
    db.commit()
    db.refresh(invitation)
    return user_invitation_out(invitation, user.email)


@app.post("/api/v1/user-invitations/accept")
def accept_user_invitation(
    payload: UserInvitationAcceptRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    validated = validate_user_invitation(db, payload.token, settings=settings)
    if validated is None:
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation is invalid or expired")
    invitation, user = validated
    organization = db.get(Organization, invitation.organization_id)
    if organization is None or not organization.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation is invalid or expired")
    if user.password_ready:
        if account_is_locked(user):
            write_audit(
                db,
                "auth.invitation_password_blocked",
                user_id=user.id,
                organization_id=str(invitation.organization_id),
                resource_type="user_invitation",
                resource_id=invitation.id,
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Invitation acceptance temporarily unavailable",
            )
        if not verify_password(payload.password, user.password_hash):
            user.failed_login_count += 1
            action = "auth.invitation_password_failed"
            if user.failed_login_count >= settings.login_max_attempts:
                user.locked_until = utcnow() + timedelta(seconds=settings.login_lockout_seconds)
                action = "auth.invitation_password_locked"
            write_audit(
                db,
                action,
                user_id=user.id,
                organization_id=str(invitation.organization_id),
                resource_type="user_invitation",
                resource_id=invitation.id,
            )
            db.commit()
            status_code = (
                status.HTTP_429_TOO_MANY_REQUESTS
                if action == "auth.invitation_password_locked"
                else status.HTTP_403_FORBIDDEN
            )
            detail = (
                "Invitation acceptance temporarily unavailable"
                if status_code == status.HTTP_429_TOO_MANY_REQUESTS
                else "Current password is incorrect"
            )
            raise HTTPException(status_code=status_code, detail=detail)
        user.failed_login_count = 0
        user.locked_until = None
    else:
        user.password_hash = hash_password(payload.password)
        user.password_ready = True
        user.password_changed_at = utcnow()
    role = str((invitation.context or {}).get("role") or "viewer")
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == invitation.organization_id,
            OrganizationMembership.user_id == user.id,
        )
    )
    if membership is None:
        membership = OrganizationMembership(
            organization_id=str(invitation.organization_id),
            user_id=user.id,
            role=role,
            active=True,
        )
        db.add(membership)
    else:
        membership.role = role
        membership.active = True
        touch_membership(membership)
    now = utcnow()
    user.active = True
    user.session_version += 1
    for active in db.scalars(
        select(AccountAccessToken).where(
            AccountAccessToken.user_id == user.id,
            AccountAccessToken.organization_id == invitation.organization_id,
            AccountAccessToken.purpose == USER_INVITATION_PURPOSE,
            AccountAccessToken.used_at.is_(None),
        )
    ).all():
        active.used_at = now
        active.delivery_status = "delivered"
        active.delivery_detail = "Invitation accepted"
    write_audit(
        db,
        "user.invitation_accepted",
        user_id=user.id,
        organization_id=str(invitation.organization_id),
        resource_type="user_invitation",
        resource_id=invitation.id,
        details={"role": role},
    )
    db.commit()
    return {"status": "invitation_accepted"}


@app.delete("/api/v1/user-invitations/{invitation_id}", response_model=UserInvitationOut)
def revoke_user_invitation(
    invitation_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserInvitationOut:
    organization_id = organization_id_from_context(auth_context)
    result = db.execute(
        select(AccountAccessToken, User.email)
        .join(User, User.id == AccountAccessToken.user_id)
        .where(
            AccountAccessToken.id == invitation_id,
            AccountAccessToken.organization_id == organization_id,
            AccountAccessToken.purpose == USER_INVITATION_PURPOSE,
        )
    ).first()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    invitation, email = result
    if invitation.used_at is None:
        invitation.used_at = utcnow()
    invitation.delivery_status = "failed"
    invitation.delivery_detail = "Invitation revoked"
    write_audit(
        db,
        "user.invitation_revoked",
        user_id=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        organization_id=organization_id,
        resource_type="user_invitation",
        resource_id=invitation.id,
    )
    db.commit()
    db.refresh(invitation)
    return user_invitation_out(invitation, email)


@app.post("/api/v1/users", response_model=UserOut)
def create_user(
    payload: UserCreateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserOut:
    if not auth_context.get("legacy"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Use one-time user invitations for dashboard accounts",
        )
    organization_id = organization_id_from_context(auth_context)
    if payload.role == "owner" and auth_context.get("role") != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required")
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        user = User(email=email, password_hash=hash_password(payload.password), role=payload.role, active=True)
        db.add(user)
        db.flush()
    existing = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user.id,
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already belongs to this workspace")
    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user.id,
        role=payload.role,
        active=True,
    )
    user.active = True
    db.add(membership)
    db.flush()
    write_audit(
        db,
        "user.created",
        user_id=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        organization_id=organization_id,
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email, "role": membership.role},
    )
    db.commit()
    db.refresh(user)
    return user_out(user, membership.role, membership.active)


@app.patch("/api/v1/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserOut:
    organization_id = organization_id_from_context(auth_context)
    user = db.get(User, user_id)
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    if user is None or membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if (
        membership.role == "owner" or payload.role == "owner"
    ) and auth_context.get("role") != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required")
    removing_privileged_access = membership.active and membership.role in {"owner", "admin"} and (
        payload.active is False or payload.role == "viewer"
    )
    if removing_privileged_access and count_active_workspace_admins(
        db, organization_id, exclude_user_id=user.id
    ) == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="At least one active administrator is required",
        )
    security_changed = False
    if payload.role is not None and payload.role != membership.role:
        membership.role = payload.role
        security_changed = True
    if payload.active is not None and payload.active != membership.active:
        membership.active = payload.active
        security_changed = True
    if payload.password is not None:
        if not auth_context.get("legacy"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Use self-service password recovery for dashboard accounts",
            )
        membership_count = db.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.active.is_(True),
            )
        ) or 0
        if membership_count > 1 and user.id != auth_context.get("uid"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Multi-workspace users must change their own password",
            )
        user.password_hash = hash_password(payload.password)
        user.password_changed_at = utcnow()
        security_changed = True
    user.active = bool(
        db.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.active.is_(True),
            )
        )
    )
    touch_membership(membership)
    if security_changed:
        user.session_version += 1
    write_audit(
        db,
        "user.updated",
        user_id=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        organization_id=organization_id,
        resource_type="user",
        resource_id=user.id,
        details={
            "role": membership.role,
            "active": membership.active,
            "credentials_rotated": payload.password is not None,
        },
    )
    db.commit()
    db.refresh(user)
    return user_out(user, membership.role, membership.active)


@app.post("/api/v1/users/{user_id}/mfa-reset")
def reset_user_mfa(
    user_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    organization_id = organization_id_from_context(auth_context)
    if not auth_context.get("legacy") and auth_context.get("role") != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required")
    if not auth_context.get("legacy") and auth_context.get("uid") == user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another owner must reset your MFA",
        )
    membership = db.scalar(
        select(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
        .with_for_update()
    )
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None or membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.mfa_enabled_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA is not enabled")
    disable_mfa(db, user)
    write_audit(
        db,
        "user.mfa_reset",
        user_id=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        organization_id=organization_id,
        resource_type="user",
        resource_id=user.id,
        details={"target_email": user.email},
    )
    db.commit()
    return {"status": "mfa_reset"}


@app.get("/api/v1/sites", response_model=list[SiteOut])
def list_sites(
    auth_context: dict = Depends(require_operations_read_access),
    db: Session = Depends(get_db),
) -> list[Site]:
    organization_id = organization_id_from_context(auth_context)
    return list(
        db.scalars(
            select(Site).where(Site.organization_id == organization_id).order_by(Site.created_at.asc())
        ).all()
    )


@app.post("/api/v1/sites", response_model=SiteOut)
def create_site(
    payload: SiteCreateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Site:
    organization_id = organization_id_from_context(auth_context)
    name = payload.name.strip()
    existing = db.scalar(
        select(Site).where(Site.organization_id == organization_id, Site.name == name)
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Site already exists")
    site = Site(organization_id=organization_id, name=name)
    db.add(site)
    db.flush()
    write_audit(
        db,
        "site.created",
        organization_id=organization_id,
        resource_type="site",
        resource_id=site.id,
        details={"name": site.name},
    )
    db.commit()
    db.refresh(site)
    return site


@app.patch("/api/v1/sites/{site_id}", response_model=SiteOut)
def update_site(
    site_id: str,
    payload: SiteUpdateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Site:
    organization_id = organization_id_from_context(auth_context)
    site = get_site_or_404(db, site_id, organization_id)
    name = payload.name.strip()
    duplicate = db.scalar(
        select(Site).where(
            Site.organization_id == organization_id,
            Site.name == name,
            Site.id != site.id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Site already exists")
    site.name = name
    write_audit(
        db,
        "site.updated",
        organization_id=organization_id,
        resource_type="site",
        resource_id=site.id,
        details={"name": site.name},
    )
    db.commit()
    db.refresh(site)
    return site


@app.get("/api/v1/onboarding/status", response_model=OnboardingStatusOut)
def onboarding_status(
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> OnboardingStatusOut:
    organization_id = organization_id_from_context(auth_context)
    site_ids = select(Site.id).where(Site.organization_id == organization_id)
    sites = db.scalar(select(func.count(Site.id)).where(Site.organization_id == organization_id)) or 0
    sensors = list(db.scalars(select(Sensor).where(Sensor.site_id.in_(site_ids))).all())
    completed_scans = db.scalar(
        select(func.count(ScanRun.id)).where(ScanRun.site_id.in_(site_ids), ScanRun.status == "completed")
    ) or 0
    reports = db.scalar(select(func.count(Report.id)).where(Report.site_id.in_(site_ids))) or 0
    schedules = db.scalar(select(func.count(ScanSchedule.id)).where(ScanSchedule.site_id.in_(site_ids))) or 0
    notifications = db.scalar(
        select(func.count(NotificationEndpoint.id)).where(
            NotificationEndpoint.organization_id == organization_id,
            NotificationEndpoint.enabled.is_(True),
        )
    ) or 0
    return OnboardingStatusOut(
        api_connected=True,
        sites_created=sites > 0,
        sensor_registered=len(sensors) > 0,
        worker_online=any(sensor.disabled_at is None and sensor_connection_state(sensor) == "online" for sensor in sensors),
        first_scan_completed=completed_scans > 0,
        first_report_generated=reports > 0,
        schedule_configured=schedules > 0,
        notifications_configured=notifications > 0,
    )


@app.post(
    "/api/v1/sensors/register",
    response_model=SensorRegisterResponse,
)
def register_sensor(
    payload: SensorRegisterRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SensorRegisterResponse:
    organization_id = organization_id_from_context(auth_context)
    site = db.scalar(
        select(Site).where(
            Site.organization_id == organization_id,
            Site.name == payload.site_name,
        )
    )
    if site is None:
        site = Site(organization_id=organization_id, name=payload.site_name)
        db.add(site)
        db.flush()

    token = generate_sensor_token()
    sensor = Sensor(
        site_id=site.id,
        name=payload.name,
        hostname=payload.hostname,
        status="registered",
        token_hash=hash_secret(token),
    )
    db.add(sensor)
    db.flush()
    write_audit(
        db,
        "sensor.registered",
        sensor_id=sensor.id,
        organization_id=organization_id,
        resource_type="sensor",
        resource_id=sensor.id,
        details={"name": sensor.name, "site_name": site.name},
    )
    db.commit()
    return SensorRegisterResponse(sensor_id=sensor.id, sensor_token=token, site_id=site.id)


@app.get("/api/v1/sensor-enrollments", response_model=list[SensorEnrollmentOut])
def list_sensor_enrollments(
    site_id: str | None = None,
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> list[SensorEnrollmentOut]:
    organization_id = organization_id_from_context(auth_context)
    query = (
        select(SensorEnrollment)
        .where(SensorEnrollment.organization_id == organization_id)
        .order_by(SensorEnrollment.created_at.desc())
        .limit(100)
    )
    if site_id:
        get_site_or_404(db, site_id, organization_id)
        query = query.where(SensorEnrollment.site_id == site_id)
    return [sensor_enrollment_out(db, row) for row in db.scalars(query).all()]


@app.post("/api/v1/sensor-enrollments", response_model=SensorEnrollmentCreateResponse)
def create_sensor_enrollment(
    payload: SensorEnrollmentCreateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SensorEnrollmentCreateResponse:
    organization_id = organization_id_from_context(auth_context)
    get_site_or_404(db, payload.site_id, organization_id)
    token = generate_sensor_token()
    enrollment = SensorEnrollment(
        organization_id=organization_id,
        site_id=payload.site_id,
        label=payload.label.strip(),
        token_hash=hash_secret(token),
        created_by=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        expires_at=utcnow() + timedelta(minutes=payload.expires_in_minutes),
    )
    db.add(enrollment)
    db.flush()
    write_audit(
        db,
        "sensor_enrollment.created",
        user_id=enrollment.created_by,
        organization_id=organization_id,
        resource_type="sensor_enrollment",
        resource_id=enrollment.id,
        details={"site_id": enrollment.site_id, "expires_at": enrollment.expires_at.isoformat()},
    )
    db.commit()
    db.refresh(enrollment)
    base = sensor_enrollment_out(db, enrollment)
    return SensorEnrollmentCreateResponse(**base.model_dump(), enrollment_token=token)


@app.delete("/api/v1/sensor-enrollments/{enrollment_id}", response_model=SensorEnrollmentOut)
def revoke_sensor_enrollment(
    enrollment_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SensorEnrollmentOut:
    organization_id = organization_id_from_context(auth_context)
    enrollment = db.scalar(
        select(SensorEnrollment).where(
            SensorEnrollment.id == enrollment_id,
            SensorEnrollment.organization_id == organization_id,
        )
    )
    if enrollment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor enrollment not found")
    if enrollment.used_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Used enrollment cannot be revoked")
    enrollment.revoked_at = enrollment.revoked_at or utcnow()
    write_audit(
        db,
        "sensor_enrollment.revoked",
        user_id=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        organization_id=organization_id,
        resource_type="sensor_enrollment",
        resource_id=enrollment.id,
    )
    db.commit()
    db.refresh(enrollment)
    return sensor_enrollment_out(db, enrollment)


@app.get("/api/v1/integration-tokens", response_model=list[IntegrationTokenOut])
def list_integration_tokens(
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[IntegrationTokenOut]:
    organization_id = organization_id_from_context(auth_context)
    tokens = db.scalars(
        select(IntegrationToken)
        .where(IntegrationToken.organization_id == organization_id)
        .order_by(IntegrationToken.created_at.desc())
    ).all()
    return [integration_token_out(token) for token in tokens]


@app.post("/api/v1/integration-tokens", response_model=IntegrationTokenCreateResponse)
def create_integration_token(
    payload: IntegrationTokenCreateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IntegrationTokenCreateResponse:
    organization_id = organization_id_from_context(auth_context)
    scopes = sorted(set(payload.scopes))
    invalid_scopes = set(scopes) - ALLOWED_INTEGRATION_TOKEN_SCOPES
    if invalid_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported integration scope: {sorted(invalid_scopes)[0]}",
        )
    secret = generate_integration_token()
    token = IntegrationToken(
        organization_id=organization_id,
        name=payload.name.strip(),
        token_hash=hash_secret(secret),
        scopes=scopes,
        created_by=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        expires_at=utcnow() + timedelta(days=payload.expires_in_days),
    )
    db.add(token)
    db.flush()
    write_audit(
        db,
        "integration_token.created",
        user_id=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        organization_id=organization_id,
        resource_type="integration_token",
        resource_id=token.id,
        details={"name": token.name, "scopes": scopes, "expires_at": token.expires_at.isoformat()},
    )
    db.commit()
    db.refresh(token)
    return IntegrationTokenCreateResponse(
        **integration_token_out(token).model_dump(),
        access_token=secret,
    )


@app.get("/api/v1/integration-tokens/self", response_model=IntegrationTokenOut)
def inspect_integration_token(
    auth_context: dict = Depends(require_integration_token_access),
    db: Session = Depends(get_db),
) -> IntegrationTokenOut:
    token = db.get(IntegrationToken, str(auth_context["integration_token_id"]))
    if token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration token not found")
    return integration_token_out(token)


@app.post(
    "/api/v1/integration-tokens/{token_id}/rotate",
    response_model=IntegrationTokenCreateResponse,
)
def rotate_integration_token(
    token_id: str,
    payload: IntegrationTokenRotateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IntegrationTokenCreateResponse:
    organization_id = organization_id_from_context(auth_context)
    previous = db.scalar(
        select(IntegrationToken).where(
            IntegrationToken.id == token_id,
            IntegrationToken.organization_id == organization_id,
        )
    )
    if previous is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration token not found")
    if integration_token_out(previous).state != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active integration tokens can be rotated")

    secret = generate_integration_token()
    replacement = IntegrationToken(
        organization_id=organization_id,
        name=previous.name,
        token_hash=hash_secret(secret),
        scopes=list(previous.scopes or []),
        created_by=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        expires_at=utcnow() + timedelta(days=payload.expires_in_days),
    )
    db.add(replacement)
    db.flush()
    write_audit(
        db,
        "integration_token.rotated",
        user_id=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        organization_id=organization_id,
        resource_type="integration_token",
        resource_id=previous.id,
        details={
            "name": previous.name,
            "scopes": list(previous.scopes or []),
            "replacement_id": replacement.id,
            "replacement_expires_at": replacement.expires_at.isoformat(),
            "previous_remains_active": True,
        },
    )
    db.commit()
    db.refresh(replacement)
    return IntegrationTokenCreateResponse(
        **integration_token_out(replacement).model_dump(),
        access_token=secret,
    )


@app.delete("/api/v1/integration-tokens/{token_id}", response_model=IntegrationTokenOut)
def revoke_integration_token(
    token_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IntegrationTokenOut:
    organization_id = organization_id_from_context(auth_context)
    token = db.scalar(
        select(IntegrationToken).where(
            IntegrationToken.id == token_id,
            IntegrationToken.organization_id == organization_id,
        )
    )
    if token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration token not found")
    if token.revoked_at is None:
        token.revoked_at = utcnow()
        write_audit(
            db,
            "integration_token.revoked",
            user_id=str(auth_context.get("uid")) if auth_context.get("uid") else None,
            organization_id=organization_id,
            resource_type="integration_token",
            resource_id=token.id,
            details={"name": token.name, "scopes": list(token.scopes or [])},
        )
        db.commit()
        db.refresh(token)
    return integration_token_out(token)


@app.post("/api/v1/sensors/enroll", response_model=SensorRegisterResponse)
def enroll_sensor(payload: SensorEnrollRequest, db: Session = Depends(get_db)) -> SensorRegisterResponse:
    enrollment = db.scalar(
        select(SensorEnrollment)
        .where(SensorEnrollment.token_hash == hash_secret(payload.enrollment_token))
        .with_for_update()
    )
    now = utcnow()
    unavailable = enrollment is None
    if enrollment is not None:
        expires_at = enrollment.expires_at
        comparable_now = now.replace(tzinfo=None) if expires_at.tzinfo is None else now
        unavailable = bool(
            enrollment.used_at is not None
            or enrollment.revoked_at is not None
            or expires_at <= comparable_now
        )
    if unavailable or enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enrollment token is invalid or unavailable",
        )
    site = get_site_or_404(db, enrollment.site_id, enrollment.organization_id)
    sensor_token = generate_sensor_token()
    sensor = Sensor(
        site_id=site.id,
        name=payload.name.strip(),
        hostname=payload.hostname.strip() if payload.hostname else None,
        status="registered",
        token_hash=hash_secret(sensor_token),
    )
    enrollment.used_at = now
    db.add(sensor)
    db.flush()
    write_audit(
        db,
        "sensor.enrolled",
        sensor_id=sensor.id,
        organization_id=enrollment.organization_id,
        resource_type="sensor",
        resource_id=sensor.id,
        details={"site_id": site.id, "enrollment_id": enrollment.id, "name": sensor.name},
    )
    db.commit()
    return SensorRegisterResponse(sensor_id=sensor.id, sensor_token=sensor_token, site_id=site.id)


@app.post("/api/v1/sensors/{sensor_id}/heartbeat")
def heartbeat(
    payload: HeartbeatIn,
    sensor: Sensor = Depends(require_sensor_for_path),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if sensor.disabled_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sensor is disabled")
    previous = (
        sensor.status,
        sensor.version,
        sensor.os_name,
        sensor.worker_state,
        sensor.current_job_id,
        sensor.last_error,
    )
    sensor.status = payload.status
    sensor.last_seen_at = utcnow()
    sensor.version = payload.details.get("version") or sensor.version
    sensor.os_name = payload.details.get("os") or payload.details.get("os_name") or sensor.os_name
    sensor.hostname = payload.details.get("hostname") or sensor.hostname
    sensor.worker_state = payload.details.get("state") or sensor.worker_state
    sensor.current_job_id = payload.details.get("job_id")
    sensor.last_error = payload.details.get("last_error") or None
    current = (
        sensor.status,
        sensor.version,
        sensor.os_name,
        sensor.worker_state,
        sensor.current_job_id,
        sensor.last_error,
    )
    if current != previous:
        organization_id = get_site_or_404(db, sensor.site_id).organization_id
        write_audit(
            db,
            "sensor.state_changed",
            sensor_id=sensor.id,
            organization_id=organization_id,
            resource_type="sensor",
            resource_id=sensor.id,
            details=payload.details,
        )
    db.commit()
    return {"status": "ok"}


@app.get("/api/v1/sensors", response_model=list[SensorOut])
def list_sensors(
    site_id: str | None = None,
    auth_context: dict = Depends(require_operations_read_access),
    db: Session = Depends(get_db),
) -> list[SensorOut]:
    organization_id = organization_id_from_context(auth_context)
    query = (
        select(Sensor)
        .join(Site, Site.id == Sensor.site_id)
        .where(Site.organization_id == organization_id)
        .order_by(Sensor.created_at.asc())
    )
    if site_id:
        get_site_or_404(db, site_id, organization_id)
        query = query.where(Sensor.site_id == site_id)
    sensors = list(db.scalars(query).all())
    return [sensor_out(db, sensor) for sensor in sensors]


@app.patch("/api/v1/sensors/{sensor_id}", response_model=SensorOut)
def update_sensor(
    sensor_id: str,
    payload: SensorUpdateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SensorOut:
    organization_id = organization_id_from_context(auth_context)
    sensor = get_sensor_for_organization(db, sensor_id, organization_id)
    if payload.name is not None:
        sensor.name = payload.name.strip()
    if payload.hostname is not None:
        sensor.hostname = payload.hostname.strip() or None
    if payload.status is not None:
        sensor.status = payload.status
    if payload.last_error is not None:
        sensor.last_error = payload.last_error
    write_audit(db, "sensor.updated", sensor_id=sensor.id, organization_id=organization_id, resource_type="sensor", resource_id=sensor.id)
    db.commit()
    db.refresh(sensor)
    return sensor_out(db, sensor)


@app.post("/api/v1/sensors/{sensor_id}/rotate-token", response_model=SensorRotateResponse)
def rotate_sensor_token(
    sensor_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SensorRotateResponse:
    organization_id = organization_id_from_context(auth_context)
    sensor = get_sensor_for_organization(db, sensor_id, organization_id)
    token = generate_sensor_token()
    sensor.token_hash = hash_secret(token)
    sensor.status = "registered"
    sensor.last_seen_at = None
    write_audit(db, "sensor.token_rotated", sensor_id=sensor.id, organization_id=organization_id, resource_type="sensor", resource_id=sensor.id)
    db.commit()
    return SensorRotateResponse(sensor_id=sensor.id, sensor_token=token)


@app.post("/api/v1/sensors/{sensor_id}/disable", response_model=SensorOut)
def disable_sensor(
    sensor_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SensorOut:
    organization_id = organization_id_from_context(auth_context)
    sensor = get_sensor_for_organization(db, sensor_id, organization_id)
    sensor.disabled_at = utcnow()
    sensor.status = "disabled"
    db.query(ScanJob).filter(ScanJob.sensor_id == sensor.id, ScanJob.status == "queued").update(
        {"status": "canceled", "updated_at": utcnow(), "error_message": "Sensor disabled"}
    )
    write_audit(db, "sensor.disabled", sensor_id=sensor.id, organization_id=organization_id, resource_type="sensor", resource_id=sensor.id)
    db.commit()
    db.refresh(sensor)
    return sensor_out(db, sensor)


@app.post("/api/v1/sensors/{sensor_id}/enable", response_model=SensorOut)
def enable_sensor(
    sensor_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SensorOut:
    organization_id = organization_id_from_context(auth_context)
    sensor = get_sensor_for_organization(db, sensor_id, organization_id)
    sensor.disabled_at = None
    sensor.status = "registered"
    sensor.last_error = None
    write_audit(db, "sensor.enabled", sensor_id=sensor.id, organization_id=organization_id, resource_type="sensor", resource_id=sensor.id)
    db.commit()
    db.refresh(sensor)
    return sensor_out(db, sensor)


@app.post("/api/v1/scan-jobs", response_model=ScanJobOut)
def create_scan_job(
    payload: ScanJobCreateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ScanJob:
    organization_id = organization_id_from_context(auth_context)
    target_cidr = normalize_scan_job_target(payload.target_cidr)
    if payload.sensor_id:
        sensor = get_sensor_for_organization(db, payload.sensor_id, organization_id)
    else:
        sensor = db.scalar(
            select(Sensor)
            .join(Site, Site.id == Sensor.site_id)
            .where(Site.organization_id == organization_id, Sensor.disabled_at.is_(None))
            .order_by(Sensor.created_at.asc())
        )
    if sensor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Register a sensor before queueing scans")
    if sensor.disabled_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sensor is disabled")

    job = ScanJob(
        site_id=sensor.site_id,
        sensor_id=sensor.id,
        target_cidr=target_cidr,
        include_wifi=payload.include_wifi,
        status="queued",
        preview={},
        result_summary={},
    )
    db.add(job)
    db.flush()
    write_audit(
        db,
        "scan_job.created",
        sensor_id=sensor.id,
        organization_id=organization_id,
        resource_type="scan_job",
        resource_id=job.id,
        details={"target_cidr": target_cidr, "include_wifi": payload.include_wifi},
    )
    db.commit()
    db.refresh(job)
    return job


@app.get("/api/v1/scan-jobs", response_model=list[ScanJobOut])
def list_scan_jobs(
    status_filter: str | None = None,
    sensor_id: str | None = None,
    site_id: str | None = None,
    auth_context: dict = Depends(require_operations_read_access),
    db: Session = Depends(get_db),
) -> list[ScanJob]:
    organization_id = organization_id_from_context(auth_context)
    query = (
        select(ScanJob)
        .join(Site, Site.id == ScanJob.site_id)
        .where(Site.organization_id == organization_id)
        .order_by(ScanJob.created_at.desc())
    )
    if status_filter:
        query = query.where(ScanJob.status == status_filter)
    if sensor_id:
        query = query.where(ScanJob.sensor_id == sensor_id)
    if site_id:
        query = query.where(ScanJob.site_id == site_id)
    return list(db.scalars(query).all())


@app.post("/api/v1/scan-jobs/{job_id}/cancel", response_model=ScanJobOut)
def cancel_scan_job(
    job_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ScanJob:
    organization_id = organization_id_from_context(auth_context)
    job = get_scan_job_for_organization(db, job_id, organization_id)
    if job.status in TERMINAL_SCAN_JOB_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scan job is already terminal")
    job.status = "canceled"
    job.updated_at = utcnow()
    job.completed_at = job.completed_at or job.updated_at
    write_audit(db, "scan_job.canceled", sensor_id=job.sensor_id, organization_id=organization_id, resource_type="scan_job", resource_id=job.id)
    db.commit()
    db.refresh(job)
    return job


@app.post("/api/v1/scan-jobs/{job_id}/retry", response_model=ScanJobOut)
def retry_scan_job(
    job_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ScanJob:
    organization_id = organization_id_from_context(auth_context)
    original = get_scan_job_for_organization(db, job_id, organization_id)
    if original.status not in {"failed", "canceled"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only failed or canceled scan jobs can be retried")
    retried = ScanJob(
        site_id=original.site_id,
        sensor_id=original.sensor_id,
        target_cidr=original.target_cidr,
        include_wifi=original.include_wifi,
        status="queued",
        preview={},
        result_summary={},
    )
    db.add(retried)
    db.flush()
    write_audit(
        db,
        "scan_job.retried",
        sensor_id=original.sensor_id,
        organization_id=organization_id,
        resource_type="scan_job",
        resource_id=retried.id,
        details={"original_job_id": original.id},
    )
    db.commit()
    db.refresh(retried)
    return retried


@app.get("/api/v1/scan-schedules", response_model=list[ScanScheduleOut])
def list_scan_schedules(
    site_id: str | None = None,
    auth_context: dict = Depends(require_operations_read_access),
    db: Session = Depends(get_db),
) -> list[ScanSchedule]:
    organization_id = organization_id_from_context(auth_context)
    query = (
        select(ScanSchedule)
        .join(Site, Site.id == ScanSchedule.site_id)
        .where(Site.organization_id == organization_id)
        .order_by(ScanSchedule.created_at.desc())
    )
    if site_id:
        query = query.where(ScanSchedule.site_id == site_id)
    return list(db.scalars(query).all())


@app.post("/api/v1/scan-schedules", response_model=ScanScheduleOut)
def create_scan_schedule(
    payload: ScanScheduleCreateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ScanSchedule:
    organization_id = organization_id_from_context(auth_context)
    target_cidr = normalize_scan_job_target(payload.target_cidr)
    site, sensor = pick_site_and_sensor(
        db, payload.site_id, payload.sensor_id, organization_id
    )
    frequency = normalize_frequency(payload.frequency)
    schedule = ScanSchedule(
        site_id=site.id,
        sensor_id=sensor.id,
        name=payload.name.strip(),
        target_cidr=target_cidr,
        frequency=frequency,
        time_of_day=payload.time_of_day,
        timezone=payload.timezone,
        day_of_week=payload.day_of_week,
        include_wifi=payload.include_wifi,
        enabled=payload.enabled,
        next_run_at=compute_next_run_at(
            frequency=frequency,
            time_of_day=payload.time_of_day,
            timezone_name=payload.timezone,
            day_of_week=payload.day_of_week,
        )
        if payload.enabled
        else None,
    )
    db.add(schedule)
    db.flush()
    write_audit(
        db,
        "scan_schedule.created",
        sensor_id=sensor.id,
        organization_id=organization_id,
        resource_type="scan_schedule",
        resource_id=schedule.id,
        details={"target_cidr": target_cidr, "frequency": frequency},
    )
    db.commit()
    db.refresh(schedule)
    return schedule


@app.patch("/api/v1/scan-schedules/{schedule_id}", response_model=ScanScheduleOut)
def update_scan_schedule(
    schedule_id: str,
    payload: ScanScheduleUpdateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ScanSchedule:
    organization_id = organization_id_from_context(auth_context)
    schedule = get_scan_schedule_for_organization(db, schedule_id, organization_id)
    if payload.sensor_id is not None:
        sensor = get_sensor_for_organization(db, payload.sensor_id, organization_id)
        if sensor.disabled_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enabled sensor not found")
        if sensor.site_id != schedule.site_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sensor belongs to another site")
        schedule.sensor_id = sensor.id
    if payload.name is not None:
        schedule.name = payload.name.strip()
    if payload.target_cidr is not None:
        schedule.target_cidr = normalize_scan_job_target(payload.target_cidr)
    if payload.frequency is not None:
        schedule.frequency = normalize_frequency(payload.frequency)
    if payload.time_of_day is not None:
        schedule.time_of_day = payload.time_of_day
    if payload.timezone is not None:
        schedule.timezone = payload.timezone
    if payload.day_of_week is not None:
        schedule.day_of_week = payload.day_of_week
    if payload.include_wifi is not None:
        schedule.include_wifi = payload.include_wifi
    if payload.enabled is not None:
        schedule.enabled = payload.enabled
    schedule.next_run_at = (
        compute_next_run_at(
            frequency=schedule.frequency,
            time_of_day=schedule.time_of_day,
            timezone_name=schedule.timezone,
            day_of_week=schedule.day_of_week,
        )
        if schedule.enabled
        else None
    )
    schedule.updated_at = utcnow()
    write_audit(db, "scan_schedule.updated", organization_id=organization_id, resource_type="scan_schedule", resource_id=schedule.id)
    db.commit()
    db.refresh(schedule)
    return schedule


@app.delete("/api/v1/scan-schedules/{schedule_id}")
def delete_scan_schedule(
    schedule_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    organization_id = organization_id_from_context(auth_context)
    schedule = get_scan_schedule_for_organization(db, schedule_id, organization_id)
    db.delete(schedule)
    write_audit(db, "scan_schedule.deleted", organization_id=organization_id, resource_type="scan_schedule", resource_id=schedule_id)
    db.commit()
    return {"status": "deleted"}


@app.post("/api/v1/scan-schedules/run-due", response_model=RunDueSchedulesResponse)
def run_due_scan_schedules(
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RunDueSchedulesResponse:
    scoped_organization_id = None if auth_context.get("legacy") else organization_id_from_context(auth_context)
    jobs = enqueue_due_schedules(db, organization_id=scoped_organization_id)
    for job in jobs:
        organization_id = get_site_or_404(db, job.site_id).organization_id
        write_audit(
            db,
            "scan_schedule.job_queued",
            sensor_id=job.sensor_id,
            organization_id=organization_id,
            resource_type="scan_job",
            resource_id=job.id,
            details={"schedule_id": job.schedule_id, "target_cidr": job.target_cidr},
        )
    db.commit()
    return RunDueSchedulesResponse(queued=len(jobs), job_ids=[job.id for job in jobs])


@app.post("/api/v1/sensors/{sensor_id}/scan-jobs/claim", response_model=ScanJobOut | None)
def claim_scan_job(
    sensor: Sensor = Depends(require_sensor_for_path),
    db: Session = Depends(get_db),
) -> ScanJob | None:
    if sensor.disabled_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sensor is disabled")
    recover_stale_scan_jobs(db, sensor.id)
    job = db.scalar(
        select(ScanJob)
        .where(ScanJob.sensor_id == sensor.id, ScanJob.status == "queued")
        .order_by(ScanJob.created_at.asc())
    )
    if job is None:
        return None

    now = utcnow()
    job.status = "claimed"
    job.claimed_at = now
    job.updated_at = now
    sensor.status = "online"
    sensor.last_seen_at = now
    organization_id = get_site_or_404(db, sensor.site_id).organization_id
    write_audit(db, "scan_job.claimed", sensor_id=sensor.id, organization_id=organization_id, resource_type="scan_job", resource_id=job.id)
    db.commit()
    db.refresh(job)
    return job


@app.post("/api/v1/sensors/{sensor_id}/scan-jobs/{job_id}/start", response_model=ScanJobOut)
def start_scan_job(
    job_id: str,
    payload: ScanJobStartRequest,
    sensor: Sensor = Depends(require_sensor_for_path),
    db: Session = Depends(get_db),
) -> ScanJob:
    if sensor.disabled_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sensor is disabled")
    job = get_sensor_job(db, sensor, job_id)
    if job.status in TERMINAL_SCAN_JOB_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scan job is already terminal")
    now = utcnow()
    job.status = "running"
    job.started_at = job.started_at or now
    job.updated_at = now
    job.preview = payload.preview
    sensor.status = "scanning"
    sensor.last_seen_at = now
    organization_id = get_site_or_404(db, sensor.site_id).organization_id
    write_audit(db, "scan_job.started", sensor_id=sensor.id, organization_id=organization_id, resource_type="scan_job", resource_id=job.id)
    db.commit()
    db.refresh(job)
    return job


@app.post("/api/v1/sensors/{sensor_id}/scan-jobs/{job_id}/fail", response_model=ScanJobOut)
def fail_scan_job(
    job_id: str,
    payload: ScanJobFailRequest,
    sensor: Sensor = Depends(require_sensor_for_path),
    db: Session = Depends(get_db),
) -> ScanJob:
    if sensor.disabled_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sensor is disabled")
    job = get_sensor_job(db, sensor, job_id)
    if job.status in TERMINAL_SCAN_JOB_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scan job is already terminal")
    now = utcnow()
    job.status = "failed"
    job.error_message = payload.error_message[:2000]
    job.completed_at = now
    job.updated_at = now
    sensor.status = "online"
    sensor.last_seen_at = now
    organization_id = get_site_or_404(db, sensor.site_id).organization_id
    write_audit(
        db,
        "scan_job.failed",
        sensor_id=sensor.id,
        organization_id=organization_id,
        resource_type="scan_job",
        resource_id=job.id,
        details={"error_message": job.error_message},
    )
    db.commit()
    db.refresh(job)
    return job


@app.post("/api/v1/scans", response_model=ScanIngestResponse)
def ingest_scan_endpoint(
    payload: ScanIn,
    x_sensor_token: str | None = Header(default=None, alias="X-Sensor-Token"),
    db: Session = Depends(get_db),
) -> ScanIngestResponse:
    sensor = authenticate_sensor(db, payload.sensor_id, x_sensor_token)
    if sensor.disabled_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sensor is disabled")
    scan_job = None
    if payload.scan_job_id:
        scan_job = get_sensor_job(db, sensor, payload.scan_job_id)
        if scan_job.status in TERMINAL_SCAN_JOB_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scan job is already terminal")

    scan, findings = ingest_scan(db, sensor, payload)
    organization_id = get_site_or_404(db, sensor.site_id).organization_id
    for finding in findings:
        export_finding(finding)
        if finding.severity in {"critical", "high"}:
            notify_event(
                db,
                "high_finding",
                finding_notification_payload(finding),
                site_id=finding.site_id,
            )
        if finding.type == "new_device":
            notify_event(
                db,
                "new_device",
                finding_notification_payload(finding),
                site_id=finding.site_id,
            )
        if finding.type == "risky_open_port":
            notify_event(
                db,
                "risky_service",
                finding_notification_payload(finding),
                site_id=finding.site_id,
            )
    if scan_job:
        now = utcnow()
        scan_job.status = "completed"
        scan_job.started_at = scan_job.started_at or payload.started_at or scan.started_at or now
        scan_job.completed_at = now
        scan_job.updated_at = now
        scan_job.result_summary = {
            "scan_id": scan.id,
            "assets_seen": len(payload.assets),
            "wifi_networks_seen": len(payload.wifi_networks),
            "findings_created": len({finding.id for finding in findings}),
        }
        sensor.status = "online"
        sensor.last_seen_at = now
    write_audit(
        db,
        "scan.ingested",
        sensor_id=sensor.id,
        organization_id=organization_id,
        resource_type="scan",
        resource_id=scan.id,
        details={
            "assets_seen": len(payload.assets),
            "wifi_networks_seen": len(payload.wifi_networks),
            "scan_job_id": payload.scan_job_id,
        },
    )
    notify_event(
        db,
        "scan_completed",
        {
            "title": "Scan completed",
            "summary": f"Scan completed with {len(payload.assets)} assets, {len(payload.wifi_networks)} Wi-Fi networks, and {len({finding.id for finding in findings})} findings.",
            "scan_id": scan.id,
            "scan_job_id": payload.scan_job_id,
        },
        site_id=sensor.site_id,
    )
    db.commit()
    return ScanIngestResponse(
        scan_id=scan.id,
        assets_seen=len(payload.assets),
        wifi_networks_seen=len(payload.wifi_networks),
        findings_created=len({finding.id for finding in findings}),
    )


@app.get("/api/v1/assets", response_model=list[AssetOut])
def list_assets(
    status_filter: str | None = None,
    vendor: str | None = None,
    site_id: str | None = None,
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> list[Asset]:
    organization_id = organization_id_from_context(auth_context)
    query = (
        select(Asset)
        .join(Site, Site.id == Asset.site_id)
        .where(Site.organization_id == organization_id)
        .order_by(Asset.last_seen_at.desc())
    )
    if site_id:
        query = query.where(Asset.site_id == site_id)
    if status_filter:
        query = query.where(Asset.status == status_filter)
    if vendor:
        query = query.where(Asset.vendor.ilike(f"%{vendor}%"))
    return list(db.scalars(query).all())


@app.get("/api/v1/assets/{asset_id}", response_model=AssetDetailOut)
def get_asset(
    asset_id: str,
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> AssetDetailOut:
    asset = get_asset_or_404(db, asset_id, organization_id_from_context(auth_context))
    observations = list(
        db.scalars(
            select(AssetObservation)
            .where(AssetObservation.asset_id == asset.id)
            .order_by(AssetObservation.observed_at.desc())
            .limit(50)
        ).all()
    )
    findings = list(
        db.scalars(select(Finding).where(Finding.asset_id == asset.id).order_by(Finding.created_at.desc())).all()
    )
    return AssetDetailOut(
        asset=asset,
        observations=observations,
        findings=findings,
        timeline=build_asset_timeline(asset, observations, findings),
    )


@app.get("/api/v1/wifi-networks", response_model=list[WifiNetworkOut])
def list_wifi_networks(
    site_id: str | None = None,
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> list[WifiNetwork]:
    organization_id = organization_id_from_context(auth_context)
    query = (
        select(WifiNetwork)
        .join(Site, Site.id == WifiNetwork.site_id)
        .where(Site.organization_id == organization_id)
        .order_by(WifiNetwork.last_seen_at.desc())
    )
    if site_id:
        query = query.where(WifiNetwork.site_id == site_id)
    return list(db.scalars(query).all())


@app.get("/api/v1/baselines", response_model=list[BaselineRuleOut])
def list_baselines(
    site_id: str | None = None,
    kind: str | None = None,
    status_filter: str | None = "active",
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> list[BaselineRule]:
    organization_id = organization_id_from_context(auth_context)
    query = (
        select(BaselineRule)
        .join(Site, Site.id == BaselineRule.site_id)
        .where(Site.organization_id == organization_id)
        .order_by(BaselineRule.created_at.desc())
    )
    if site_id:
        query = query.where(BaselineRule.site_id == site_id)
    if kind:
        if kind not in ALLOWED_FINDING_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid baseline kind")
        query = query.where(BaselineRule.kind == kind)
    if status_filter:
        query = query.where(BaselineRule.status == status_filter)
    return list(db.scalars(query).all())


@app.post("/api/v1/baselines", response_model=BaselineRuleOut)
def create_baseline(
    payload: BaselineRuleCreateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BaselineRule:
    get_site_or_404(db, payload.site_id, organization_id_from_context(auth_context))
    rule, _ = create_or_update_baseline(
        db,
        site_id=payload.site_id,
        kind=payload.kind,
        matcher=payload.matcher,
        finding_types=payload.finding_types,
        reason=payload.reason,
        created_by=payload.created_by,
        expires_at=payload.expires_at,
    )
    db.commit()
    db.refresh(rule)
    return rule


@app.post(
    "/api/v1/assets/{asset_id}/baseline",
    response_model=BaselineRuleOut,
)
def create_asset_baseline(
    asset_id: str,
    payload: BaselineFromEntityRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BaselineRule:
    asset = get_asset_or_404(db, asset_id, organization_id_from_context(auth_context))
    rule, _ = create_or_update_baseline(
        db,
        site_id=asset.site_id,
        kind="asset",
        matcher={"asset_id": asset.id},
        finding_types=payload.finding_types or default_finding_types("asset"),
        reason=payload.reason,
        created_by=payload.created_by,
        expires_at=payload.expires_at,
    )
    db.commit()
    db.refresh(rule)
    return rule


@app.post(
    "/api/v1/services/{service_id}/baseline",
    response_model=BaselineRuleOut,
)
def create_service_baseline(
    service_id: str,
    payload: BaselineFromEntityRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BaselineRule:
    organization_id = organization_id_from_context(auth_context)
    service = get_service_or_404(db, service_id, organization_id)
    asset = get_asset_or_404(db, service.asset_id)
    rule, _ = create_or_update_baseline(
        db,
        site_id=asset.site_id,
        kind="service",
        matcher={
            "asset_id": asset.id,
            "port": service.port,
            "protocol": service.protocol,
        },
        finding_types=payload.finding_types or default_finding_types("service"),
        reason=payload.reason,
        created_by=payload.created_by,
        expires_at=payload.expires_at,
    )
    db.commit()
    db.refresh(rule)
    return rule


@app.post(
    "/api/v1/wifi-networks/{wifi_id}/baseline",
    response_model=BaselineRuleOut,
)
def create_wifi_baseline(
    wifi_id: str,
    payload: BaselineFromEntityRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BaselineRule:
    wifi = get_wifi_or_404(db, wifi_id, organization_id_from_context(auth_context))
    if not wifi.bssid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wi-Fi baseline requires an observed BSSID",
        )
    rule, _ = create_or_update_baseline(
        db,
        site_id=wifi.site_id,
        kind="wifi",
        matcher={"bssid": wifi.bssid},
        finding_types=payload.finding_types or default_finding_types("wifi"),
        reason=payload.reason,
        created_by=payload.created_by,
        expires_at=payload.expires_at,
    )
    db.commit()
    db.refresh(rule)
    return rule


@app.patch(
    "/api/v1/baselines/{baseline_id}",
    response_model=BaselineRuleOut,
)
def update_baseline(
    baseline_id: str,
    payload: BaselineRuleUpdateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BaselineRule:
    organization_id = organization_id_from_context(auth_context)
    rule = get_baseline_or_404(db, baseline_id, organization_id)
    old_status = rule.status
    fields = payload.model_fields_set
    if "reason" in fields:
        rule.reason = payload.reason.strip() if payload.reason else None
    if "expires_at" in fields:
        rule.expires_at = payload.expires_at
    if payload.status:
        rule.status = payload.status
    rule.updated_at = utcnow()
    affected = 0
    if old_status != rule.status and rule.status == "disabled":
        affected = release_rule_findings(db, rule)
    elif rule.status == "active":
        affected = apply_rule_to_existing_findings(db, rule)
    write_audit(
        db,
        "baseline.updated",
        organization_id=organization_id,
        resource_type="baseline",
        resource_id=rule.id,
        details={"status": rule.status, "findings_updated": affected},
    )
    db.commit()
    db.refresh(rule)
    return rule


@app.delete(
    "/api/v1/baselines/{baseline_id}",
    response_model=BaselineRuleOut,
)
def disable_baseline(
    baseline_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BaselineRule:
    organization_id = organization_id_from_context(auth_context)
    rule = get_baseline_or_404(db, baseline_id, organization_id)
    rule.status = "disabled"
    rule.updated_at = utcnow()
    affected = release_rule_findings(db, rule)
    write_audit(
        db,
        "baseline.disabled",
        organization_id=organization_id,
        resource_type="baseline",
        resource_id=rule.id,
        details={"findings_reopened": affected},
    )
    db.commit()
    db.refresh(rule)
    return rule


@app.get("/api/v1/findings", response_model=list[FindingOut])
def list_findings(
    severity: str | None = None,
    status_filter: str | None = None,
    site_id: str | None = None,
    type_filter: str | None = None,
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> list[Finding]:
    organization_id = organization_id_from_context(auth_context)
    query = (
        select(Finding)
        .join(Site, Site.id == Finding.site_id)
        .where(Site.organization_id == organization_id)
        .order_by(Finding.created_at.desc())
    )
    if site_id:
        query = query.where(Finding.site_id == site_id)
    if severity:
        query = query.where(Finding.severity == severity)
    if status_filter:
        query = query.where(Finding.status == status_filter)
    if type_filter:
        query = query.where(Finding.type == type_filter)
    return list(db.scalars(query).all())


@app.get("/api/v1/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(
    action: str | None = None,
    resource_type: str | None = None,
    sensor_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    organization_id = organization_id_from_context(auth_context)
    query = select(AuditLog).where(AuditLog.organization_id == organization_id).order_by(AuditLog.created_at.desc())
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if sensor_id:
        query = query.where(AuditLog.sensor_id == sensor_id)
    return list(db.scalars(query.limit(limit)).all())


@app.get("/api/v1/findings/{finding_id}", response_model=FindingDetailOut)
def get_finding(
    finding_id: str,
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> FindingDetailOut:
    finding = get_finding_or_404(db, finding_id, organization_id_from_context(auth_context))
    notes = list(
        db.scalars(
            select(FindingNote).where(FindingNote.finding_id == finding.id).order_by(FindingNote.created_at.asc())
        ).all()
    )
    return FindingDetailOut(
        id=finding.id,
        site_id=finding.site_id,
        asset_id=finding.asset_id,
        wifi_network_id=finding.wifi_network_id,
        type=finding.type,
        severity=finding.severity,
        status=finding.status,
        title=finding.title,
        summary=finding.summary,
        evidence=finding.evidence,
        mitre_attack=finding.mitre_attack,
        created_at=finding.created_at,
        updated_at=finding.updated_at,
        notes=notes,
    )


@app.post("/api/v1/findings/{finding_id}/status", response_model=FindingOut)
def update_finding_status(
    finding_id: str,
    status_value: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Finding:
    organization_id = organization_id_from_context(auth_context)
    if status_value not in {"open", "acknowledged", "resolved", "false_positive"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid finding status")
    finding = get_finding_or_404(db, finding_id, organization_id)
    finding.status = status_value
    finding.updated_at = utcnow()
    write_audit(
        db,
        "finding.status_updated",
        organization_id=organization_id,
        resource_type="finding",
        resource_id=finding.id,
        details={"status": status_value},
    )
    db.commit()
    db.refresh(finding)
    return finding


@app.post("/api/v1/findings/{finding_id}/notes", response_model=FindingNoteOut)
def create_finding_note(
    finding_id: str,
    payload: FindingNoteCreateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FindingNote:
    organization_id = organization_id_from_context(auth_context)
    finding = get_finding_or_404(db, finding_id, organization_id)
    note = FindingNote(finding_id=finding.id, author=payload.author.strip(), body=payload.body.strip())
    finding.updated_at = utcnow()
    db.add(note)
    db.flush()
    write_audit(
        db,
        "finding.note_created",
        organization_id=organization_id,
        resource_type="finding",
        resource_id=finding.id,
        details={"note_id": note.id},
    )
    db.commit()
    db.refresh(note)
    return note


@app.post("/api/v1/findings/{finding_id}/verify", response_model=ScanJobOut)
def verify_finding(
    finding_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ScanJob:
    organization_id = organization_id_from_context(auth_context)
    finding = get_finding_or_404(db, finding_id, organization_id)
    if not finding.asset_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only asset findings can be verified by rescan")
    asset = db.get(Asset, finding.asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Affected asset not found")
    sensor = db.scalar(
        select(Sensor)
        .where(Sensor.site_id == finding.site_id, Sensor.disabled_at.is_(None))
        .order_by(Sensor.created_at.asc())
    )
    if sensor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No enabled sensor available for this site")
    target_cidr = normalize_scan_job_target(cidr_for_asset(asset))
    job = ScanJob(
        site_id=finding.site_id,
        sensor_id=sensor.id,
        target_cidr=target_cidr,
        include_wifi=False,
        status="queued",
        preview={},
        result_summary={},
    )
    db.add(job)
    db.flush()
    write_audit(
        db,
        "finding.verify_queued",
        sensor_id=sensor.id,
        organization_id=organization_id,
        resource_type="finding",
        resource_id=finding.id,
        details={"scan_job_id": job.id, "target_cidr": target_cidr},
    )
    db.commit()
    db.refresh(job)
    return job


@app.post("/api/v1/reports/generate", response_model=ReportOut)
def generate_report(
    site_id: str | None = None,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Report:
    organization_id = organization_id_from_context(auth_context)
    site = (
        get_site_or_404(db, site_id, organization_id)
        if site_id
        else db.scalar(
            select(Site)
            .where(Site.organization_id == organization_id)
            .order_by(Site.created_at.asc())
        )
    )
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No site has been registered")
    report = build_report(db, site.id)
    export_report(report)
    write_audit(db, "report.generated", organization_id=organization_id, resource_type="report", resource_id=report.id)
    notify_event(
        db,
        "scheduled_report_ready",
        {"title": report.title, "summary": report.summary, "risk_level": report.risk_level, "report_id": report.id},
        site_id=report.site_id,
    )
    db.commit()
    db.refresh(report)
    return report


@app.get("/api/v1/reports", response_model=list[ReportOut])
def list_reports(
    site_id: str | None = None,
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> list[Report]:
    organization_id = organization_id_from_context(auth_context)
    query = (
        select(Report)
        .join(Site, Site.id == Report.site_id)
        .where(Site.organization_id == organization_id)
        .order_by(Report.created_at.desc())
    )
    if site_id:
        query = query.where(Report.site_id == site_id)
    return list(db.scalars(query).all())


@app.get("/api/v1/reports/{report_id}", response_model=ReportOut)
def get_report(
    report_id: str,
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> Report:
    return get_report_or_404(db, report_id, organization_id_from_context(auth_context))


@app.get("/api/v1/reports/{report_id}/export.html", response_class=HTMLResponse)
def export_report_html(
    report_id: str,
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    report = get_report_or_404(db, report_id, organization_id_from_context(auth_context))
    site = db.get(Site, report.site_id)
    return HTMLResponse(
        content=render_report_html(report, site),
        headers={"Content-Disposition": f'attachment; filename="{report_export_filename(report)}"'},
    )


@app.get("/api/v1/reports/{report_id}/export.pdf")
def export_report_pdf(
    report_id: str,
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> Response:
    report = get_report_or_404(db, report_id, organization_id_from_context(auth_context))
    site = db.get(Site, report.site_id)
    pdf = render_report_pdf(report, site.name if site else "Unknown site")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_export_filename(report, "pdf")}"'},
    )


@app.get(
    "/api/v1/notification-endpoints",
    response_model=list[NotificationEndpointOut],
)
def list_notification_endpoints(
    site_id: str | None = None,
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> list[NotificationEndpoint]:
    organization_id = organization_id_from_context(auth_context)
    query = select(NotificationEndpoint).where(NotificationEndpoint.organization_id == organization_id).order_by(NotificationEndpoint.created_at.desc())
    if site_id:
        query = query.where((NotificationEndpoint.site_id == site_id) | (NotificationEndpoint.site_id.is_(None)))
    return list(db.scalars(query).all())


@app.post(
    "/api/v1/notification-endpoints",
    response_model=NotificationEndpointOut,
)
def create_notification_endpoint(
    payload: NotificationEndpointCreateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NotificationEndpoint:
    organization_id = organization_id_from_context(auth_context)
    if payload.site_id:
        get_site_or_404(db, payload.site_id, organization_id)
    endpoint = NotificationEndpoint(
        organization_id=organization_id,
        site_id=payload.site_id,
        name=payload.name.strip(),
        type=payload.type,
        target=payload.target.strip(),
        enabled=payload.enabled,
        events=payload.events,
    )
    db.add(endpoint)
    db.flush()
    write_audit(
        db,
        "notification_endpoint.created",
        organization_id=organization_id,
        resource_type="notification_endpoint",
        resource_id=endpoint.id,
        details={"type": endpoint.type, "name": endpoint.name},
    )
    db.commit()
    db.refresh(endpoint)
    return endpoint


@app.patch(
    "/api/v1/notification-endpoints/{endpoint_id}",
    response_model=NotificationEndpointOut,
)
def update_notification_endpoint(
    endpoint_id: str,
    payload: NotificationEndpointUpdateRequest,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NotificationEndpoint:
    organization_id = organization_id_from_context(auth_context)
    endpoint = db.scalar(select(NotificationEndpoint).where(NotificationEndpoint.id == endpoint_id, NotificationEndpoint.organization_id == organization_id))
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification endpoint not found")
    if payload.name is not None:
        endpoint.name = payload.name.strip()
    if payload.target is not None:
        endpoint.target = payload.target.strip()
    if payload.events is not None:
        endpoint.events = payload.events
    if payload.enabled is not None:
        endpoint.enabled = payload.enabled
    endpoint.updated_at = utcnow()
    write_audit(db, "notification_endpoint.updated", organization_id=organization_id, resource_type="notification_endpoint", resource_id=endpoint.id)
    db.commit()
    db.refresh(endpoint)
    return endpoint


@app.delete("/api/v1/notification-endpoints/{endpoint_id}")
def delete_notification_endpoint(
    endpoint_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    organization_id = organization_id_from_context(auth_context)
    endpoint = db.scalar(select(NotificationEndpoint).where(NotificationEndpoint.id == endpoint_id, NotificationEndpoint.organization_id == organization_id))
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification endpoint not found")
    db.delete(endpoint)
    write_audit(db, "notification_endpoint.deleted", organization_id=organization_id, resource_type="notification_endpoint", resource_id=endpoint_id)
    db.commit()
    return {"status": "deleted"}


@app.post(
    "/api/v1/notification-endpoints/{endpoint_id}/test",
    response_model=NotificationTestResponse,
)
def send_test_notification(
    endpoint_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NotificationTestResponse:
    organization_id = organization_id_from_context(auth_context)
    endpoint = db.scalar(select(NotificationEndpoint).where(NotificationEndpoint.id == endpoint_id, NotificationEndpoint.organization_id == organization_id))
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification endpoint not found")
    delivery = test_notification(db, endpoint)
    ok = delivery.status == "delivered"
    detail = delivery.response_detail or delivery.status
    write_audit(
        db,
        "notification_endpoint.tested",
        organization_id=organization_id,
        resource_type="notification_endpoint",
        resource_id=endpoint.id,
        details={"ok": ok, "detail": detail, "delivery_id": delivery.id},
    )
    db.commit()
    return NotificationTestResponse(ok=ok, detail=detail)


@app.get(
    "/api/v1/notification-deliveries",
    response_model=list[NotificationDeliveryOut],
)
def list_notification_deliveries(
    endpoint_id: str | None = None,
    delivery_status: str | None = Query(default=None, alias="status", pattern="^(queued|retrying|delivered|failed)$"),
    limit: int = Query(default=50, ge=1, le=250),
    auth_context: dict = Depends(require_operator),
    db: Session = Depends(get_db),
) -> list[NotificationDelivery]:
    organization_id = organization_id_from_context(auth_context)
    query = select(NotificationDelivery).where(NotificationDelivery.organization_id == organization_id)
    if endpoint_id:
        query = query.where(NotificationDelivery.endpoint_id == endpoint_id)
    if delivery_status:
        query = query.where(NotificationDelivery.status == delivery_status)
    query = query.order_by(NotificationDelivery.created_at.desc()).limit(limit)
    return list(db.scalars(query).all())


@app.post(
    "/api/v1/notification-deliveries/run-due",
    response_model=NotificationRunResponse,
)
def run_due_notification_deliveries(
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NotificationRunResponse:
    organization_id = None if auth_context.get("legacy") else organization_id_from_context(auth_context)
    result = process_due_deliveries(db, organization_id=organization_id)
    write_audit(
        db,
        "notification_delivery.run_due",
        organization_id=organization_id or organization_id_from_context(auth_context),
        resource_type="notification_delivery",
        details=result,
    )
    db.commit()
    return NotificationRunResponse(**result)


@app.post(
    "/api/v1/account-access/run-due",
    response_model=AccountAccessRunResponse,
)
def run_due_account_access_deliveries(
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AccountAccessRunResponse:
    result = process_due_account_access_deliveries(db, settings=settings)
    write_audit(
        db,
        "account_access_delivery.run_due",
        organization_id=organization_id_from_context(auth_context),
        resource_type="account_access_token",
        details=result,
    )
    db.commit()
    return AccountAccessRunResponse(**result)


def account_access_delivery_out(row: AccountAccessToken, email: str) -> AccountAccessDeliveryOut:
    return AccountAccessDeliveryOut(
        id=row.id,
        user_id=row.user_id,
        email=email,
        purpose=row.purpose,
        status=row.delivery_status,
        attempts=row.delivery_attempts,
        max_attempts=row.max_delivery_attempts,
        expires_at=row.expires_at,
        next_attempt_at=row.next_attempt_at,
        last_attempt_at=row.last_attempt_at,
        delivered_at=row.delivered_at,
        detail=row.delivery_detail,
        created_at=row.created_at,
    )


@app.get(
    "/api/v1/account-access/deliveries",
    response_model=list[AccountAccessDeliveryOut],
)
def list_account_access_deliveries(
    limit: int = Query(default=25, ge=1, le=100),
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AccountAccessDeliveryOut]:
    organization_id = organization_id_from_context(auth_context)
    rows = db.execute(
        select(AccountAccessToken, User.email)
        .join(User, User.id == AccountAccessToken.user_id)
        .outerjoin(
            OrganizationMembership,
            and_(
                OrganizationMembership.user_id == User.id,
                OrganizationMembership.organization_id == organization_id,
            ),
        )
        .where(
            or_(
                AccountAccessToken.organization_id == organization_id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
        .order_by(AccountAccessToken.created_at.desc())
        .limit(limit)
    ).all()
    return [account_access_delivery_out(row, email) for row, email in rows]


@app.post(
    "/api/v1/account-access/deliveries/{delivery_id}/retry",
    response_model=AccountAccessDeliveryOut,
)
def retry_account_access_delivery(
    delivery_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AccountAccessDeliveryOut:
    organization_id = organization_id_from_context(auth_context)
    result = db.execute(
        select(AccountAccessToken, User.email)
        .join(User, User.id == AccountAccessToken.user_id)
        .outerjoin(
            OrganizationMembership,
            and_(
                OrganizationMembership.user_id == User.id,
                OrganizationMembership.organization_id == organization_id,
            ),
        )
        .where(
            AccountAccessToken.id == delivery_id,
            or_(
                AccountAccessToken.organization_id == organization_id,
                OrganizationMembership.organization_id == organization_id,
            ),
        )
    ).first()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account access delivery not found")
    row, email = result
    now = utcnow()
    comparison_now = now if row.expires_at.tzinfo else now.replace(tzinfo=None)
    if row.used_at is not None or row.expires_at <= comparison_now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account access link is expired or already used")
    row.delivery_status = "queued"
    row.delivery_attempts = 0
    row.next_attempt_at = now
    row.delivery_detail = None
    attempt_account_access_delivery(db, row, settings=settings)
    write_audit(
        db,
        "account_access_delivery.retried",
        organization_id=organization_id,
        user_id=str(auth_context.get("uid")) if auth_context.get("uid") else None,
        resource_type="account_access_token",
        resource_id=row.id,
        details={"status": row.delivery_status},
    )
    db.commit()
    return account_access_delivery_out(row, email)


@app.post(
    "/api/v1/notification-deliveries/{delivery_id}/retry",
    response_model=NotificationDeliveryOut,
)
def retry_notification_delivery(
    delivery_id: str,
    auth_context: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NotificationDelivery:
    organization_id = organization_id_from_context(auth_context)
    delivery = db.scalar(select(NotificationDelivery).where(NotificationDelivery.id == delivery_id, NotificationDelivery.organization_id == organization_id))
    if delivery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification delivery not found")
    endpoint = db.get(NotificationEndpoint, delivery.endpoint_id)
    if endpoint is None or not endpoint.enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notification endpoint is disabled or unavailable")
    delivery.status = "queued"
    delivery.attempts = 0
    delivery.next_attempt_at = utcnow()
    delivery.response_detail = None
    attempt_delivery(db, delivery, endpoint=endpoint, settings=settings)
    write_audit(
        db,
        "notification_delivery.retried",
        organization_id=organization_id,
        resource_type="notification_delivery",
        resource_id=delivery.id,
        details={"status": delivery.status, "attempts": delivery.attempts},
    )
    db.commit()
    db.refresh(delivery)
    return delivery


@app.get("/api/v1/core/export")
def export_core_bundle(
    auth_context: dict = Depends(require_core_export_access),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return build_core_export(db, organization_id=organization_id_from_context(auth_context))
