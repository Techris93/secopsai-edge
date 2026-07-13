from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ServiceObservation:
    port: int
    protocol: str = "tcp"
    state: str = "open"
    name: str | None = None
    product: str | None = None
    version: str | None = None


@dataclass(slots=True)
class AssetObservation:
    ip: str
    mac: str | None = None
    vendor: str | None = None
    hostname: str | None = None
    os_guess: str | None = None
    device_type: str | None = None
    services: list[ServiceObservation] = field(default_factory=list)
    observed_at: datetime = field(default_factory=utcnow)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WifiNetworkObservation:
    ssid: str
    bssid: str | None = None
    channel: int | None = None
    signal: int | None = None
    encryption: str | None = None
    observed_at: datetime = field(default_factory=utcnow)
    source: str = "unknown"


@dataclass(slots=True)
class ScanResult:
    sensor_id: str
    target_cidr: str
    scan_job_id: str | None = None
    scan_source: str = "nmap"
    started_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None
    assets: list[AssetObservation] = field(default_factory=list)
    wifi_networks: list[WifiNetworkObservation] = field(default_factory=list)

    def complete(self) -> "ScanResult":
        self.completed_at = utcnow()
        return self
