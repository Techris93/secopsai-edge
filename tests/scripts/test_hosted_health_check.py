from __future__ import annotations

import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


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
                    "schema_revision": "0016_wifi_provenance",
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
