from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from secopsai_api.models import Asset, BaselineRule, Finding, FindingNote, Service, WifiNetwork, utcnow


BASELINE_KINDS = {"asset", "service", "wifi"}
ALLOWED_FINDING_TYPES = {
    "asset": {"new_device", "vendor_unknown", "missing_device"},
    "service": {"risky_open_port", "port_change"},
    "wifi": {"duplicate_ssid", "weak_wifi"},
}
DEFAULT_FINDING_TYPES = {
    "asset": ["new_device", "vendor_unknown"],
    "service": ["risky_open_port", "port_change"],
    "wifi": ["duplicate_ssid"],
}


def active_rules(db: Session, site_id: str, kind: str) -> list[BaselineRule]:
    now = utcnow()
    rules = db.scalars(
        select(BaselineRule).where(
            BaselineRule.site_id == site_id,
            BaselineRule.kind == kind,
            BaselineRule.status == "active",
        )
    ).all()
    return [rule for rule in rules if not rule.expires_at or _aware(rule.expires_at) > now]


def is_baselined(
    db: Session,
    site_id: str,
    kind: str,
    finding_type: str,
    *,
    asset: Asset | None = None,
    service: Service | Any | None = None,
    wifi: WifiNetwork | None = None,
) -> bool:
    context = _context(asset=asset, service=service, wifi=wifi)
    for rule in active_rules(db, site_id, kind):
        if rule.finding_types and finding_type not in rule.finding_types:
            continue
        if _matcher_matches(rule.matcher, context):
            return True
    return False


def apply_rule_to_existing_findings(db: Session, rule: BaselineRule) -> int:
    changed = 0
    findings = db.scalars(
        select(Finding).where(
            Finding.site_id == rule.site_id,
            Finding.status.in_(["open", "acknowledged"]),
        )
    ).all()
    for finding in findings:
        if not finding_matches_rule(db, finding, rule):
            continue
        evidence = dict(finding.evidence or {})
        evidence["baseline"] = {
            "rule_id": rule.id,
            "reason": rule.reason,
            "applied_at": utcnow().isoformat(),
        }
        finding.evidence = evidence
        finding.status = "acknowledged"
        finding.updated_at = utcnow()
        if not db.scalar(
            select(FindingNote).where(
                FindingNote.finding_id == finding.id,
                FindingNote.body.contains(rule.id),
            )
        ):
            db.add(
                FindingNote(
                    finding_id=finding.id,
                    author=rule.created_by,
                    body=f"Approved baseline {rule.id}: {rule.reason or 'Approved by operator.'}",
                )
            )
        changed += 1
    return changed


def release_rule_findings(db: Session, rule: BaselineRule) -> int:
    changed = 0
    findings = db.scalars(
        select(Finding).where(Finding.site_id == rule.site_id, Finding.status == "acknowledged")
    ).all()
    for finding in findings:
        evidence = dict(finding.evidence or {})
        baseline = evidence.get("baseline")
        if not isinstance(baseline, dict) or baseline.get("rule_id") != rule.id:
            continue
        evidence.pop("baseline", None)
        finding.evidence = evidence
        finding.status = "open"
        finding.updated_at = utcnow()
        changed += 1
    return changed


def finding_matches_rule(db: Session, finding: Finding, rule: BaselineRule) -> bool:
    if rule.finding_types and finding.type not in rule.finding_types:
        return False
    asset = db.get(Asset, finding.asset_id) if finding.asset_id else None
    wifi = db.get(WifiNetwork, finding.wifi_network_id) if finding.wifi_network_id else None
    service = None
    if rule.kind == "service" and asset:
        port = _int_or_none((finding.evidence or {}).get("port"))
        protocol = str((finding.evidence or {}).get("protocol") or "tcp")
        if port is not None:
            service = db.scalar(
                select(Service).where(
                    Service.asset_id == asset.id,
                    Service.port == port,
                    Service.protocol == protocol,
                )
            )
    context = _context(asset=asset, service=service, wifi=wifi, evidence=finding.evidence or {})
    return _matcher_matches(rule.matcher, context)


def default_finding_types(kind: str) -> list[str]:
    return list(DEFAULT_FINDING_TYPES[kind])


def _context(
    *,
    asset: Asset | None = None,
    service: Service | Any | None = None,
    wifi: WifiNetwork | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    values = dict(evidence or {})
    if asset:
        values.update(
            asset_id=asset.id,
            ip_address=asset.ip_address,
            ip=asset.ip_address,
            mac_address=asset.mac_address,
            mac=asset.mac_address,
        )
    if service:
        values.update(
            service_id=getattr(service, "id", None),
            port=getattr(service, "port", None),
            protocol=getattr(service, "protocol", None),
        )
    if wifi:
        values.update(
            wifi_network_id=wifi.id,
            ssid=wifi.ssid,
            bssid=wifi.bssid,
        )
    if "new_bssid" in values and "bssid" not in values:
        values["bssid"] = values["new_bssid"]
    return values


def _matcher_matches(matcher: dict[str, Any], context: dict[str, Any]) -> bool:
    if not matcher:
        return False
    for key, expected in matcher.items():
        if expected is None or expected == "":
            continue
        actual = context.get(key)
        if key in {"mac", "mac_address", "bssid", "protocol"}:
            if _normalized(actual) != _normalized(expected):
                return False
        elif key == "port":
            if _int_or_none(actual) != _int_or_none(expected):
                return False
        elif actual != expected:
            return False
    return True


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
