from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

import httpx

from secopsai_agent.models import ScanResult


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


class SecOpsApiClient:
    def __init__(self, base_url: str, sensor_token: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.sensor_token = sensor_token
        self.timeout = timeout

    def _sensor_headers(self) -> dict[str, str]:
        return {"X-Sensor-Token": self.sensor_token}

    def claim_scan_job(self, sensor_id: str) -> dict[str, Any] | None:
        response = httpx.post(
            f"{self.base_url}/api/v1/sensors/{sensor_id}/scan-jobs/claim",
            headers=self._sensor_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def start_scan_job(self, sensor_id: str, job_id: str, preview: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/api/v1/sensors/{sensor_id}/scan-jobs/{job_id}/start",
            headers=self._sensor_headers(),
            json={"preview": preview},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def fail_scan_job(self, sensor_id: str, job_id: str, error_message: str) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/api/v1/sensors/{sensor_id}/scan-jobs/{job_id}/fail",
            headers=self._sensor_headers(),
            json={"error_message": error_message},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def heartbeat(self, sensor_id: str, status: str = "online", details: dict[str, Any] | None = None) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/api/v1/sensors/{sensor_id}/heartbeat",
            headers=self._sensor_headers(),
            json={"status": status, "details": details or {}},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def submit_scan(self, scan: ScanResult) -> dict[str, Any]:
        payload = _json_safe(asdict(scan))
        response = httpx.post(
            f"{self.base_url}/api/v1/scans",
            headers=self._sensor_headers(),
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
