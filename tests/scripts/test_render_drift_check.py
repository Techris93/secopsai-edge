from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "render_drift_check.py"


def inventory(*, plan: str = "basic_256mb", expires_at: str | None = None) -> list[dict[str, object]]:
    return [
        {
            "service": {
                "name": "secopsai-edge-api",
                "type": "web_service",
                "repo": "https://github.com/Techris93/secopsai-edge.git",
                "branch": "main",
                "autoDeploy": "yes",
                "serviceDetails": {
                    "healthCheckPath": "/readyz",
                    "envSpecificDetails": {
                        "buildCommand": "pip install -r requirements.lock",
                        "startCommand": "./scripts/render-start-api",
                    },
                },
            }
        },
        {
            "service": {
                "name": "secopsai-edge-scheduler",
                "type": "cron_job",
                "repo": "https://github.com/Techris93/secopsai-edge",
                "branch": "main",
                "autoDeploy": True,
                "serviceDetails": {
                    "schedule": "*/5 * * * *",
                    "envSpecificDetails": {
                        "buildCommand": "pip install -r requirements.lock",
                        "startCommand": "./scripts/render-run-due-schedules",
                    },
                },
            }
        },
        {
            "postgres": {
                "name": "secopsai-edge-postgres",
                "status": "available",
                "version": "16",
                "plan": plan,
                "expiresAt": expires_at,
                "owner": {"password": "must-not-leak"},
            }
        },
    ]


def run_check(tmp_path: Path, payload: list[dict[str, object]], *args: str) -> subprocess.CompletedProcess[str]:
    fixture = tmp_path / "services.json"
    fixture.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--services-json", str(fixture), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_matching_paid_inventory_passes_without_leaking_unread_fields(tmp_path: Path) -> None:
    result = run_check(tmp_path, inventory(), "--json", "--now", "2026-07-13T00:00:00Z")

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["status"] == "ok"
    assert output["drift_count"] == 0
    assert "must-not-leak" not in result.stdout


def test_build_and_health_drift_fail_the_check(tmp_path: Path) -> None:
    payload = inventory()
    payload[0]["service"]["serviceDetails"]["healthCheckPath"] = "/healthz"  # type: ignore[index]
    payload[0]["service"]["serviceDetails"]["envSpecificDetails"]["buildCommand"] = "pip install -r api/requirements.txt"  # type: ignore[index]

    result = run_check(tmp_path, payload, "--now", "2026-07-13T00:00:00Z")

    assert result.returncode == 1
    assert "API build command" in result.stdout
    assert "API health check" in result.stdout


def test_free_database_expiry_is_reported_without_failing_by_default(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        inventory(plan="free", expires_at="2026-07-20T19:33:07Z"),
        "--json",
        "--now",
        "2026-07-13T00:00:00Z",
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["status"] == "warning"
    assert output["warning_count"] == 1
    assert output["results"][-1]["code"] == "database.expires_soon"


def test_fail_on_warning_supports_automated_risk_gates(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        inventory(plan="free", expires_at="2026-07-20T19:33:07Z"),
        "--now",
        "2026-07-13T00:00:00Z",
        "--fail-on-warning",
    )

    assert result.returncode == 1
    assert "[WARNING] Free database expires" in result.stdout
