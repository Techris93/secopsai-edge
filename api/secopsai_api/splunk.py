from __future__ import annotations

from typing import Any

import httpx

from secopsai_api.config import Settings, get_settings
from secopsai_api.models import Finding, Report


def export_finding(finding: Finding, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if not _enabled(settings):
        return
    _send(
        settings,
        {
            "event": {
                "type": "finding",
                "id": finding.id,
                "finding_type": finding.type,
                "severity": finding.severity,
                "status": finding.status,
                "title": finding.title,
                "summary": finding.summary,
                "evidence": finding.evidence,
            },
            "sourcetype": "secopsai:edge:finding",
        },
    )


def export_report(report: Report, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if not _enabled(settings):
        return
    _send(
        settings,
        {
            "event": {
                "type": "report",
                "id": report.id,
                "title": report.title,
                "summary": report.summary,
                "risk_level": report.risk_level,
            },
            "sourcetype": "secopsai:edge:report",
        },
    )


def _enabled(settings: Settings) -> bool:
    return bool(settings.splunk_hec_enabled and settings.splunk_hec_url and settings.splunk_hec_token)


def _send(settings: Settings, payload: dict[str, Any]) -> None:
    assert settings.splunk_hec_url and settings.splunk_hec_token
    response = httpx.post(
        settings.splunk_hec_url,
        headers={"Authorization": f"Splunk {settings.splunk_hec_token}"},
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
