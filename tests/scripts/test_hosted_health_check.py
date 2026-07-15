from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import hosted_health_check  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "hosted_health_check.py"


class Handler(BaseHTTPRequestHandler):
    ready = True

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._write_json({"status": "ok", "version": "test", "commit": "abc123"})
        elif self.path == "/readyz":
            self._write_json(
                {
                    "status": "ready" if self.ready else "not_ready",
                    "schema_revision": "0017_sensor_offline_alert",
                },
                200 if self.ready else 503,
            )
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
                "python3",
                str(SCRIPT),
                "--api-url",
                origin,
                "--dashboard-url",
                origin,
                "--output",
                str(tmp_path / "health.jsonl"),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_hosted_health_check_records_success_without_response_bodies(tmp_path: Path) -> None:
    result = run_check(tmp_path, ready=True)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert len(payload["checks"]) == 3
    assert "body" not in result.stdout
    assert (tmp_path / "health.jsonl").read_text(encoding="utf-8").count("\n") == 1


def test_hosted_health_check_fails_when_readiness_is_degraded(tmp_path: Path) -> None:
    result = run_check(tmp_path, ready=False)
    assert result.returncode == 1
    assert json.loads(result.stdout)["ok"] is False


def test_hosted_health_check_classifies_dns_failures_without_exposing_reason(monkeypatch) -> None:
    def raise_dns_error(*_args, **_kwargs):
        raise urllib.error.URLError(socket.gaierror(-2, "name or service not known"))

    monkeypatch.setattr(hosted_health_check.urllib.request, "urlopen", raise_dns_error)
    result = hosted_health_check.check("https://dashboard.example.test")

    assert result["ok"] is False
    assert result["error_code"] == "dns_resolution_failed"
    assert "reason" not in result


def test_hosted_health_check_classifies_http_errors_without_reading_body(monkeypatch) -> None:
    error = urllib.error.HTTPError(
        "https://dashboard.example.test",
        503,
        "unavailable",
        hdrs=None,
        fp=None,
    )

    def raise_http_error(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(hosted_health_check.urllib.request, "urlopen", raise_http_error)
    result = hosted_health_check.check("https://dashboard.example.test")

    assert result["ok"] is False
    assert result["error_code"] == "http_error"
    assert result["status_code"] == 503
    assert "body" not in result


def test_hosted_health_check_redacts_url_credentials_and_query(monkeypatch) -> None:
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, *_args):
            return b"{}"

    monkeypatch.setattr(hosted_health_check.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())
    result = hosted_health_check.check("https://user:secret@example.test/ready?token=secret", expect_json=True)

    assert result["url"] == "https://example.test/ready"
    assert "secret" not in str(result)
