from __future__ import annotations

from ipaddress import ip_network

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from secopsai_api.ai import build_report
from secopsai_api.audit import write_audit
from secopsai_api.config import get_settings
from secopsai_api.database import engine, get_db
from secopsai_api.detection import ingest_scan
from secopsai_api.models import Asset, Base, Finding, Report, ScanJob, Sensor, Site, WifiNetwork, utcnow
from secopsai_api.schemas import (
    AssetOut,
    DashboardLoginRequest,
    DashboardSessionResponse,
    FindingOut,
    HeartbeatIn,
    ReportOut,
    ScanIn,
    ScanIngestResponse,
    ScanJobCreateRequest,
    ScanJobFailRequest,
    ScanJobOut,
    ScanJobStartRequest,
    SensorRegisterRequest,
    SensorRegisterResponse,
    WifiNetworkOut,
)
from secopsai_api.security import (
    authenticate_sensor,
    constant_time_equals,
    create_dashboard_session,
    generate_sensor_token,
    hash_secret,
    require_admin,
    require_sensor_for_path,
)
from secopsai_api.splunk import export_finding, export_report


settings = get_settings()
app = FastAPI(title="SecOpsAI Edge API", version="0.1.0")
PRIVATE_SCAN_RANGES = tuple(
    ip_network(cidr) for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
TERMINAL_SCAN_JOB_STATUSES = {"completed", "failed", "canceled"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


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


@app.post("/api/v1/auth/session", response_model=DashboardSessionResponse)
def create_session(payload: DashboardLoginRequest) -> DashboardSessionResponse:
    if not constant_time_equals(payload.admin_token, settings.admin_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
    return DashboardSessionResponse(
        access_token=create_dashboard_session(),
        expires_in=settings.dashboard_session_ttl_seconds,
    )


@app.post(
    "/api/v1/sensors/register",
    response_model=SensorRegisterResponse,
    dependencies=[Depends(require_admin)],
)
def register_sensor(payload: SensorRegisterRequest, db: Session = Depends(get_db)) -> SensorRegisterResponse:
    site = db.scalar(select(Site).where(Site.name == payload.site_name))
    if site is None:
        site = Site(name=payload.site_name)
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
        resource_type="sensor",
        resource_id=sensor.id,
        details={"name": sensor.name, "site_name": site.name},
    )
    db.commit()
    return SensorRegisterResponse(sensor_id=sensor.id, sensor_token=token, site_id=site.id)


@app.post("/api/v1/sensors/{sensor_id}/heartbeat")
def heartbeat(
    payload: HeartbeatIn,
    sensor: Sensor = Depends(require_sensor_for_path),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    sensor.status = payload.status
    sensor.last_seen_at = utcnow()
    write_audit(
        db,
        "sensor.heartbeat",
        sensor_id=sensor.id,
        resource_type="sensor",
        resource_id=sensor.id,
        details=payload.details,
    )
    db.commit()
    return {"status": "ok"}


@app.post("/api/v1/scan-jobs", response_model=ScanJobOut, dependencies=[Depends(require_admin)])
def create_scan_job(payload: ScanJobCreateRequest, db: Session = Depends(get_db)) -> ScanJob:
    target_cidr = normalize_scan_job_target(payload.target_cidr)
    if payload.sensor_id:
        sensor = db.get(Sensor, payload.sensor_id)
    else:
        sensor = db.scalar(select(Sensor).order_by(Sensor.created_at.asc()))
    if sensor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Register a sensor before queueing scans")

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
        resource_type="scan_job",
        resource_id=job.id,
        details={"target_cidr": target_cidr, "include_wifi": payload.include_wifi},
    )
    db.commit()
    db.refresh(job)
    return job


@app.get("/api/v1/scan-jobs", response_model=list[ScanJobOut], dependencies=[Depends(require_admin)])
def list_scan_jobs(
    status_filter: str | None = None,
    sensor_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[ScanJob]:
    query = select(ScanJob).order_by(ScanJob.created_at.desc())
    if status_filter:
        query = query.where(ScanJob.status == status_filter)
    if sensor_id:
        query = query.where(ScanJob.sensor_id == sensor_id)
    return list(db.scalars(query).all())


@app.post("/api/v1/scan-jobs/{job_id}/cancel", response_model=ScanJobOut, dependencies=[Depends(require_admin)])
def cancel_scan_job(job_id: str, db: Session = Depends(get_db)) -> ScanJob:
    job = db.get(ScanJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan job not found")
    if job.status in TERMINAL_SCAN_JOB_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scan job is already terminal")
    job.status = "canceled"
    job.updated_at = utcnow()
    job.completed_at = job.completed_at or job.updated_at
    write_audit(db, "scan_job.canceled", sensor_id=job.sensor_id, resource_type="scan_job", resource_id=job.id)
    db.commit()
    db.refresh(job)
    return job


@app.post("/api/v1/sensors/{sensor_id}/scan-jobs/claim", response_model=ScanJobOut | None)
def claim_scan_job(
    sensor: Sensor = Depends(require_sensor_for_path),
    db: Session = Depends(get_db),
) -> ScanJob | None:
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
    write_audit(db, "scan_job.claimed", sensor_id=sensor.id, resource_type="scan_job", resource_id=job.id)
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
    write_audit(db, "scan_job.started", sensor_id=sensor.id, resource_type="scan_job", resource_id=job.id)
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
    write_audit(
        db,
        "scan_job.failed",
        sensor_id=sensor.id,
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
    scan_job = None
    if payload.scan_job_id:
        scan_job = get_sensor_job(db, sensor, payload.scan_job_id)
        if scan_job.status in TERMINAL_SCAN_JOB_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scan job is already terminal")

    scan, findings = ingest_scan(db, sensor, payload)
    for finding in findings:
        export_finding(finding)
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
        resource_type="scan",
        resource_id=scan.id,
        details={
            "assets_seen": len(payload.assets),
            "wifi_networks_seen": len(payload.wifi_networks),
            "scan_job_id": payload.scan_job_id,
        },
    )
    db.commit()
    return ScanIngestResponse(
        scan_id=scan.id,
        assets_seen=len(payload.assets),
        wifi_networks_seen=len(payload.wifi_networks),
        findings_created=len({finding.id for finding in findings}),
    )


@app.get("/api/v1/assets", response_model=list[AssetOut], dependencies=[Depends(require_admin)])
def list_assets(
    status_filter: str | None = None,
    vendor: str | None = None,
    db: Session = Depends(get_db),
) -> list[Asset]:
    query = select(Asset).order_by(Asset.last_seen_at.desc())
    if status_filter:
        query = query.where(Asset.status == status_filter)
    if vendor:
        query = query.where(Asset.vendor.ilike(f"%{vendor}%"))
    return list(db.scalars(query).all())


@app.get("/api/v1/wifi-networks", response_model=list[WifiNetworkOut], dependencies=[Depends(require_admin)])
def list_wifi_networks(db: Session = Depends(get_db)) -> list[WifiNetwork]:
    return list(db.scalars(select(WifiNetwork).order_by(WifiNetwork.last_seen_at.desc())).all())


@app.get("/api/v1/findings", response_model=list[FindingOut], dependencies=[Depends(require_admin)])
def list_findings(
    severity: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
) -> list[Finding]:
    query = select(Finding).order_by(Finding.created_at.desc())
    if severity:
        query = query.where(Finding.severity == severity)
    if status_filter:
        query = query.where(Finding.status == status_filter)
    return list(db.scalars(query).all())


@app.post("/api/v1/findings/{finding_id}/status", response_model=FindingOut, dependencies=[Depends(require_admin)])
def update_finding_status(finding_id: str, status_value: str, db: Session = Depends(get_db)) -> Finding:
    if status_value not in {"open", "acknowledged", "resolved", "false_positive"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid finding status")
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    finding.status = status_value
    finding.updated_at = utcnow()
    write_audit(
        db,
        "finding.status_updated",
        resource_type="finding",
        resource_id=finding.id,
        details={"status": status_value},
    )
    db.commit()
    db.refresh(finding)
    return finding


@app.post("/api/v1/reports/generate", response_model=ReportOut, dependencies=[Depends(require_admin)])
def generate_report(db: Session = Depends(get_db)) -> Report:
    site = db.scalar(select(Site).order_by(Site.created_at.asc()))
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No site has been registered")
    report = build_report(db, site.id)
    export_report(report)
    write_audit(db, "report.generated", resource_type="report", resource_id=report.id)
    db.commit()
    db.refresh(report)
    return report


@app.get("/api/v1/reports", response_model=list[ReportOut], dependencies=[Depends(require_admin)])
def list_reports(db: Session = Depends(get_db)) -> list[Report]:
    return list(db.scalars(select(Report).order_by(Report.created_at.desc())).all())
