from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ServiceIn(BaseModel):
    port: int = Field(ge=1, le=65535)
    protocol: str = "tcp"
    state: str = "open"
    name: str | None = None
    product: str | None = None
    version: str | None = None


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    port: int
    protocol: str
    name: str | None = None
    product: str | None = None
    version: str | None = None
    state: str
    first_seen_at: datetime
    last_seen_at: datetime


class AssetObservationIn(BaseModel):
    ip: str
    mac: str | None = None
    vendor: str | None = None
    hostname: str | None = None
    os_guess: str | None = None
    device_type: str | None = None
    services: list[ServiceIn] = Field(default_factory=list)
    observed_at: datetime | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class WifiNetworkIn(BaseModel):
    ssid: str
    bssid: str | None = None
    channel: int | None = None
    signal: float | None = None
    encryption: str | None = None
    observed_at: datetime | None = None
    source: str = "macos"


class ScanIn(BaseModel):
    sensor_id: str
    scan_job_id: str | None = None
    target_cidr: str | None = None
    scan_source: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    assets: list[AssetObservationIn] = Field(default_factory=list)
    wifi_networks: list[WifiNetworkIn] = Field(default_factory=list)


class SensorRegisterRequest(BaseModel):
    name: str
    hostname: str | None = None
    site_name: str = "Default Site"


class SensorRegisterResponse(BaseModel):
    sensor_id: str
    sensor_token: str
    site_id: str


class SiteCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class SiteUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    created_at: datetime


class DashboardLoginRequest(BaseModel):
    admin_token: str


class DashboardUserLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=512)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: str
    active: bool
    created_at: datetime
    last_login_at: datetime | None = None
    password_changed_at: datetime | None = None


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    active: bool
    role: str
    created_at: datetime


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class OrganizationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)


class WorkspaceSwitchRequest(BaseModel):
    organization_id: str = Field(min_length=36, max_length=36)


class UserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, max_length=512)
    role: str = Field(default="viewer", pattern="^(owner|admin|viewer)$")


class UserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(owner|admin|viewer)$")
    active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=512)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=12, max_length=512)


class DashboardSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut | None = None


class AuthMeOut(BaseModel):
    subject: str
    role: str
    organization_id: str
    organizations: list[OrganizationOut] = Field(default_factory=list)
    user: UserOut | None = None


class HeartbeatIn(BaseModel):
    status: str = "online"
    details: dict[str, Any] = Field(default_factory=dict)


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    ip_address: str
    mac_address: str | None = None
    vendor: str | None = None
    hostname: str | None = None
    os_guess: str | None = None
    device_type: str | None = None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    services: list[ServiceOut] = Field(default_factory=list)


class AssetObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    sensor_id: str
    scan_id: str
    asset_id: str
    ip_address: str
    mac_address: str | None = None
    vendor: str | None = None
    hostname: str | None = None
    os_guess: str | None = None
    raw_source: str | None = None
    observed_at: datetime


class AssetTimelineEventOut(BaseModel):
    id: str
    kind: str
    title: str
    summary: str
    occurred_at: datetime
    severity: str = "info"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssetDetailOut(BaseModel):
    asset: AssetOut
    observations: list[AssetObservationOut] = Field(default_factory=list)
    findings: list["FindingOut"] = Field(default_factory=list)
    timeline: list[AssetTimelineEventOut] = Field(default_factory=list)


class WifiNetworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    ssid: str
    bssid: str | None = None
    channel: int | None = None
    signal: float | None = None
    encryption: str | None = None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime


class BaselineRuleCreateRequest(BaseModel):
    site_id: str
    kind: str = Field(pattern="^(asset|service|wifi)$")
    matcher: dict[str, Any]
    finding_types: list[str] = Field(min_length=1)
    reason: str | None = Field(default=None, max_length=2000)
    created_by: str = Field(default="operator", min_length=1, max_length=120)
    expires_at: datetime | None = None


class BaselineFromEntityRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)
    finding_types: list[str] | None = None
    created_by: str = Field(default="operator", min_length=1, max_length=120)
    expires_at: datetime | None = None


class BaselineRuleUpdateRequest(BaseModel):
    status: str | None = Field(default=None, pattern="^(active|disabled)$")
    reason: str | None = Field(default=None, max_length=2000)
    expires_at: datetime | None = None


class BaselineRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    kind: str
    status: str
    matcher: dict[str, Any]
    finding_types: list[str]
    reason: str | None = None
    created_by: str
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    asset_id: str | None = None
    wifi_network_id: str | None = None
    type: str
    severity: str
    status: str
    title: str
    summary: str
    evidence: dict[str, Any]
    mitre_attack: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class FindingDetailOut(FindingOut):
    notes: list["FindingNoteOut"] = Field(default_factory=list)


class FindingNoteCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    author: str = Field(default="operator", min_length=1, max_length=120)


class FindingNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    author: str
    body: str
    created_at: datetime


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    title: str
    summary: str
    risk_level: str
    content: dict[str, Any]
    created_at: datetime


class OnboardingStatusOut(BaseModel):
    api_connected: bool
    sites_created: bool
    sensor_registered: bool
    worker_online: bool
    first_scan_completed: bool
    first_report_generated: bool
    schedule_configured: bool
    notifications_configured: bool


class ScanIngestResponse(BaseModel):
    scan_id: str
    assets_seen: int
    wifi_networks_seen: int
    findings_created: int


class ScanJobCreateRequest(BaseModel):
    target_cidr: str
    include_wifi: bool = False
    sensor_id: str | None = None


class ScanJobStartRequest(BaseModel):
    preview: dict[str, Any] = Field(default_factory=dict)


class ScanJobFailRequest(BaseModel):
    error_message: str


class ScanJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    sensor_id: str
    schedule_id: str | None = None
    target_cidr: str
    include_wifi: bool
    status: str
    created_at: datetime
    claimed_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime
    preview: dict[str, Any]
    result_summary: dict[str, Any]
    error_message: str | None = None


class ScanScheduleCreateRequest(BaseModel):
    name: str = Field(default="Daily network scan", min_length=1, max_length=160)
    site_id: str | None = None
    sensor_id: str | None = None
    target_cidr: str
    frequency: str = "daily"
    time_of_day: str = "09:00"
    timezone: str = "UTC"
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    include_wifi: bool = False
    enabled: bool = True


class ScanScheduleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    target_cidr: str | None = None
    frequency: str | None = None
    time_of_day: str | None = None
    timezone: str | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    include_wifi: bool | None = None
    enabled: bool | None = None
    sensor_id: str | None = None


class ScanScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    sensor_id: str
    name: str
    target_cidr: str
    frequency: str
    time_of_day: str
    timezone: str
    day_of_week: int | None = None
    include_wifi: bool
    enabled: bool
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RunDueSchedulesResponse(BaseModel):
    queued: int
    job_ids: list[str]


class SensorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    hostname: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=32)
    last_error: str | None = Field(default=None, max_length=2000)


class SensorRotateResponse(BaseModel):
    sensor_id: str
    sensor_token: str


class SensorOut(BaseModel):
    id: str
    site_id: str
    site_name: str
    name: str
    hostname: str | None = None
    status: str
    connection_state: str
    version: str | None = None
    os_name: str | None = None
    worker_state: str | None = None
    current_job_id: str | None = None
    last_error: str | None = None
    disabled_at: datetime | None = None
    created_at: datetime
    last_seen_at: datetime | None = None
    current_job: ScanJobOut | None = None


class NotificationEndpointCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    type: str = Field(pattern="^(webhook|email|telegram)$")
    target: str = Field(min_length=1, max_length=500)
    site_id: str | None = None
    events: list[str] = Field(default_factory=list)
    enabled: bool = True


class NotificationEndpointUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    target: str | None = Field(default=None, min_length=1, max_length=500)
    events: list[str] | None = None
    enabled: bool | None = None


class NotificationEndpointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str | None = None
    name: str
    type: str
    target: str
    enabled: bool
    events: list[str]
    last_sent_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class NotificationDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    endpoint_id: str
    site_id: str | None = None
    event_type: str
    status: str
    attempts: int
    max_attempts: int
    next_attempt_at: datetime
    last_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    response_detail: str | None = None
    created_at: datetime
    updated_at: datetime


class NotificationRunResponse(BaseModel):
    processed: int
    delivered: int
    retrying: int
    failed: int


class NotificationTestResponse(BaseModel):
    ok: bool
    detail: str


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None = None
    sensor_id: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict[str, Any]
    created_at: datetime
