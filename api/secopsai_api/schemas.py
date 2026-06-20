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


class DashboardLoginRequest(BaseModel):
    admin_token: str


class DashboardSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class HeartbeatIn(BaseModel):
    status: str = "online"
    details: dict[str, Any] = Field(default_factory=dict)


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ip_address: str
    mac_address: str | None = None
    vendor: str | None = None
    hostname: str | None = None
    os_guess: str | None = None
    device_type: str | None = None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime


class WifiNetworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ssid: str
    bssid: str | None = None
    channel: int | None = None
    signal: float | None = None
    encryption: str | None = None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
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


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: str
    risk_level: str
    content: dict[str, Any]
    created_at: datetime


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
