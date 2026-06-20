from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from secopsai_api.config import Settings, get_settings
from secopsai_api.models import Finding, Report


SENSITIVE_EVIDENCE_KEYS = {"mac", "mac_address", "bssid", "raw", "hostname"}


def build_report(db: Session, site_id: str, settings: Settings | None = None) -> Report:
    settings = settings or get_settings()
    findings = db.scalars(
        select(Finding)
        .where(Finding.site_id == site_id, Finding.status.in_(["open", "acknowledged"]))
        .order_by(Finding.created_at.desc())
        .limit(50)
    ).all()
    payload = {
        "site_id": site_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "findings": [finding_to_ai_payload(finding) for finding in findings],
    }
    content = AiReportProvider(settings).generate(payload)
    report = Report(
        site_id=site_id,
        title=content["title"],
        period_start=None,
        period_end=datetime.now(timezone.utc),
        summary=content["summary"],
        risk_level=content["risk_level"],
        content=content,
    )
    db.add(report)
    db.flush()
    return report


def finding_to_ai_payload(finding: Finding) -> dict[str, Any]:
    return {
        "type": finding.type,
        "severity": finding.severity,
        "title": finding.title,
        "summary": finding.summary,
        "evidence": redact_evidence(finding.evidence),
        "mitre_attack": finding.mitre_attack,
        "created_at": finding.created_at.isoformat(),
    }


def redact_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in evidence.items():
        if key.lower() in SENSITIVE_EVIDENCE_KEYS:
            redacted[key] = "[redacted]"
        else:
            redacted[key] = value
    return redacted


class AiReportProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.settings.ai_provider == "http" and self.settings.ai_endpoint:
            return self._generate_http(payload)
        return self._generate_mock(payload)

    def _generate_http(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.settings.ai_api_key:
            headers["Authorization"] = f"Bearer {self.settings.ai_api_key}"
        response = httpx.post(
            self.settings.ai_endpoint,
            json={"model": self.settings.ai_model, "input": payload},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "title": data.get("title", "SecOpsAI Edge Report"),
            "summary": data.get("summary", "AI report generated."),
            "risk_level": data.get("risk_level", "medium"),
            "findings": data.get("findings", payload["findings"]),
            "recommended_actions": data.get("recommended_actions", []),
            "provider": "http",
        }

    def _generate_mock(self, payload: dict[str, Any]) -> dict[str, Any]:
        findings = payload["findings"]
        severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        top = max((finding["severity"] for finding in findings), key=lambda s: severity_rank.get(s, 0), default="low")
        high_count = sum(1 for finding in findings if finding["severity"] in {"critical", "high"})
        summary = (
            f"SecOpsAI Edge found {len(findings)} active security findings. "
            f"{high_count} require priority review."
        )
        return {
            "title": "SecOpsAI Edge Weekly Security Summary",
            "summary": summary,
            "risk_level": top,
            "findings": findings,
            "recommended_actions": [
                "Validate ownership for new or unknown devices.",
                "Review exposed administrative services such as RDP, SMB, SSH, VNC, and databases.",
                "Confirm Wi-Fi SSIDs and BSSIDs match authorized infrastructure.",
            ],
            "provider": "mock",
        }
