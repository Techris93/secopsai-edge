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

    def submit_scan(self, scan: ScanResult) -> dict[str, Any]:
        payload = _json_safe(asdict(scan))
        response = httpx.post(
            f"{self.base_url}/api/v1/scans",
            headers={"X-Sensor-Token": self.sensor_token},
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
