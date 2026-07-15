#!/usr/bin/env python3
"""Run non-destructive SecOpsAI Edge controlled-pilot acceptance checks."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hosted_health_check import DEFAULT_DASHBOARD_URL, check as check_endpoint, check_dashboard


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "secopsai.edge.pilot-acceptance.v1"
SERVICE_LABEL = "ai.secopsai.edge"


def _result(name: str, ok: bool, *, required: bool, **details: Any) -> dict[str, Any]:
    return {"name": name, "ok": ok, "required": required, **details}


def _worker_check() -> dict[str, Any]:
    if platform.system() == "Darwin":
        command = ["launchctl", "print", f"gui/{os.getuid()}/{SERVICE_LABEL}"]
    elif platform.system() == "Linux":
        command = ["systemctl", "--user", "is-active", f"{SERVICE_LABEL}.service"]
    else:
        return _result(
            "worker_service",
            False,
            required=True,
            status="unsupported_platform",
            platform=platform.system().lower(),
        )
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _result("worker_service", False, required=True, status=type(exc).__name__)
    return _result(
        "worker_service",
        completed.returncode == 0,
        required=True,
        status="running" if completed.returncode == 0 else "not_running",
        platform=platform.system().lower(),
    )


def _wifi_check(*, python_bin: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [python_bin, "-m", "secopsai_agent.cli", "wifi-status"],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "agent")},
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _result("wifi_capability", False, required=False, status=type(exc).__name__)
    payload: dict[str, Any] = {}
    for line in reversed(completed.stdout.splitlines()):
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            payload = candidate
            break
    return _result(
        "wifi_capability",
        completed.returncode == 0 and bool(payload.get("supported")),
        required=False,
        status="supported" if completed.returncode == 0 and payload.get("supported") else "unavailable",
        backend=payload.get("backend"),
        interface=payload.get("interface"),
        reason=payload.get("reason"),
    )


def run_acceptance(args: argparse.Namespace) -> dict[str, Any]:
    python_bin = sys.executable
    required: list[dict[str, Any]] = []
    advisory: list[dict[str, Any]] = []

    if not args.skip_dependencies:
        nmap_path = shutil.which("nmap")
        required.append(_result("nmap", bool(nmap_path), required=True, installed=bool(nmap_path)))
        required.append(_result("python", True, required=True, version=platform.python_version()))

    if not args.skip_cloud:
        api_url = args.api_url.rstrip("/")
        dashboard_url = args.dashboard_url.rstrip("/")

        def hosted(name: str, url: str, **kwargs: Any) -> dict[str, Any]:
            return {"name": name, "required": True, **check_endpoint(url, **kwargs)}

        required.extend(
            [
                hosted("api_liveness", f"{api_url}/healthz", expect_json_status="ok"),
                hosted("api_readiness", f"{api_url}/readyz", expect_json_status="ready"),
                {"name": "dashboard", "required": True, **check_dashboard(dashboard_url)},
            ]
        )

        access_token = os.environ.get("SECOPSAI_PILOT_ACCESS_TOKEN", "").strip()
        authenticated_paths = (
            ("authenticated_identity", "/api/v1/auth/me"),
            ("authenticated_system_status", "/api/v1/system/status"),
            ("authenticated_onboarding", "/api/v1/onboarding/status"),
            ("authenticated_sites", "/api/v1/sites"),
            ("authenticated_sensors", "/api/v1/sensors"),
            ("authenticated_schedules", "/api/v1/scan-schedules"),
            ("authenticated_findings", "/api/v1/findings"),
            ("authenticated_reports", "/api/v1/reports"),
        )
        if access_token:
            auth_headers = {"Authorization": f"Bearer {access_token}"}
            required.extend(
                hosted(
                    name,
                    f"{api_url}{path}",
                    expect_json=True,
                    headers=auth_headers,
                )
                for name, path in authenticated_paths
            )
        elif args.require_auth:
            required.append(
                _result(
                    "authenticated_operator_credential",
                    False,
                    required=True,
                    status="not_configured",
                )
            )
        else:
            advisory.append(
                _result(
                    "authenticated_operator_credential",
                    False,
                    required=False,
                    status="not_configured",
                    note="Set SECOPSAI_PILOT_ACCESS_TOKEN to verify authenticated product surfaces.",
                )
            )

    if not args.skip_worker:
        required.append(_worker_check())

    if not args.skip_wifi:
        wifi = _wifi_check(python_bin=python_bin)
        wifi["required"] = bool(args.require_wifi)
        (required if args.require_wifi else advisory).append(wifi)

    required_ok = all(item.get("ok") for item in required)
    return {
        "schema_version": SCHEMA_VERSION,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "profile": "cloud" if not args.skip_cloud else "local",
        "ok": bool(required_ok),
        "required_checks": required,
        "advisories": advisory,
        "notes": [
            "No network scan, packet capture, package execution, or artifact unpacking was performed.",
            "Wi-Fi capability is advisory unless --require-wifi is supplied.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run non-destructive SecOpsAI Edge pilot acceptance checks")
    parser.add_argument("--api-url", default="https://secopsai-edge-api.onrender.com")
    parser.add_argument("--dashboard-url", default=DEFAULT_DASHBOARD_URL)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-cloud", action="store_true", help="Skip hosted API and dashboard checks")
    parser.add_argument("--skip-worker", action="store_true", help="Skip local worker-service check")
    parser.add_argument("--skip-wifi", action="store_true", help="Skip the no-scan Wi-Fi capability check")
    parser.add_argument("--require-wifi", action="store_true", help="Treat Wi-Fi capability as a required check")
    parser.add_argument(
        "--require-auth",
        action="store_true",
        help="Require SECOPSAI_PILOT_ACCESS_TOKEN and verify authenticated product surfaces",
    )
    parser.add_argument("--skip-dependencies", action="store_true", help="Skip local Nmap/Python checks")
    args = parser.parse_args()

    evidence = run_acceptance(args)
    rendered = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    print(rendered)
    if args.output:
        args.output.expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        args.output.expanduser().resolve().write_text(rendered + "\n", encoding="utf-8")
    return 0 if evidence["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
