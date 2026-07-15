from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "pilot_acceptance.py"


class Handler(BaseHTTPRequestHandler):
    ready = True

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._write_json({"status": "ok", "version": "0.3.4", "commit": "release-034"})
        elif self.path == "/readyz":
            self._write_json(
                {"status": "ready" if self.ready else "not_ready", "schema_revision": "0017_sensor_offline_alert"},
                200 if self.ready else 503,
            )
        elif self.path in {
            "/api/v1/auth/me",
            "/api/v1/system/status",
            "/api/v1/onboarding/status",
            "/api/v1/sites",
            "/api/v1/sensors",
            "/api/v1/scan-schedules",
            "/api/v1/findings",
            "/api/v1/reports",
        }:
            if self.headers.get("Authorization") != "Bearer pilot-secret":
                self._write_json({"detail": "unauthorized"}, 401)
            elif self.path == "/api/v1/auth/me":
                self._write_json({"subject": "pilot", "role": "owner"})
            elif self.path == "/api/v1/system/status":
                self._write_json({"status": "ready"})
            else:
                self._write_json([])
        else:
            body = b"<html><title>SecOpsAI Edge</title></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _write_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        return


def run_check(tmp_path: Path, *, ready: bool) -> subprocess.CompletedProcess[str]:
    Handler.ready = ready
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--api-url",
                origin,
                "--dashboard-url",
                origin,
                "--skip-worker",
                "--skip-wifi",
                "--skip-dependencies",
                "--output",
                str(tmp_path / "acceptance.json"),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_pilot_acceptance_records_non_secret_success(tmp_path: Path) -> None:
    result = run_check(tmp_path, ready=True)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert {item["name"] for item in payload["required_checks"]} == {
        "api_liveness",
        "api_readiness",
        "dashboard",
    }
    assert "body" not in result.stdout
    assert json.loads((tmp_path / "acceptance.json").read_text(encoding="utf-8"))["ok"] is True


def test_pilot_acceptance_fails_when_hosted_readiness_is_degraded(tmp_path: Path) -> None:
    result = run_check(tmp_path, ready=False)
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    readiness = next(item for item in payload["required_checks"] if item["name"] == "api_readiness")
    assert readiness["ok"] is False


def test_pilot_acceptance_verifies_authenticated_surfaces_without_printing_token(tmp_path: Path) -> None:
    Handler.ready = True
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--api-url",
                origin,
                "--dashboard-url",
                origin,
                "--skip-worker",
                "--skip-wifi",
                "--skip-dependencies",
                "--require-auth",
            ],
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "SECOPSAI_PILOT_ACCESS_TOKEN": "pilot-secret"},
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    names = {item["name"] for item in payload["required_checks"]}
    assert "authenticated_identity" in names
    assert "authenticated_reports" in names
    assert "pilot-secret" not in result.stdout


def test_pilot_acceptance_requires_auth_credential_when_requested(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--api-url",
            "http://127.0.0.1:1",
            "--dashboard-url",
            "http://127.0.0.1:1",
            "--skip-worker",
            "--skip-wifi",
            "--skip-dependencies",
            "--require-auth",
        ],
        text=True,
        capture_output=True,
        check=False,
        env={key: value for key, value in os.environ.items() if key != "SECOPSAI_PILOT_ACCESS_TOKEN"},
    )
    payload = json.loads(result.stdout)
    auth = next(item for item in payload["required_checks"] if item["name"] == "authenticated_operator_credential")
    assert auth["status"] == "not_configured"
    assert auth["ok"] is False
