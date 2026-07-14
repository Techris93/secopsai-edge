from __future__ import annotations

import json
import fcntl
import os
import plistlib
import stat
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EDGE = ROOT / "scripts" / "edge"


class _BridgeHandler(BaseHTTPRequestHandler):
    bundle = json.dumps(
        {
            "schema_version": "secopsai.edge.bundle.v1",
            "source_instance": {"organization_id": "org-pilot-1"},
            "graph": {"nodes": [], "edges": []},
            "findings": [],
        }
    ).encode()
    edge_authorization = ""
    core_authorization = ""
    core_failures_remaining = 0

    def do_GET(self):
        if self.path != "/api/v1/core/export":
            self.send_error(404)
            return
        type(self).edge_authorization = self.headers.get("Authorization", "")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.bundle)))
        self.end_headers()
        self.wfile.write(self.bundle)

    def do_POST(self):
        if self.path != "/api/v1/edge/bundles":
            self.send_error(404)
            return
        type(self).core_authorization = self.headers.get("Authorization", "")
        length = int(self.headers.get("Content-Length", "0"))
        assert self.rfile.read(length) == self.bundle
        if type(self).core_failures_remaining:
            type(self).core_failures_remaining -= 1
            self.send_error(502)
            return
        payload = json.dumps(
            {
                "status": "imported",
                "counts": {"nodes": 0, "edges": 0, "findings": 0},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


class _Server:
    def __init__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _BridgeHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def test_core_sync_service_installer_generates_supervised_timer(tmp_path: Path) -> None:
    home = tmp_path / "home"
    core = tmp_path / "core"
    output = tmp_path / "edge-bundle.json"
    config = tmp_path / "core-sync.json"
    credentials = tmp_path / "core-sync-credentials.json"
    lock = tmp_path / "core-sync.lock"
    home.mkdir()
    core.mkdir()
    env = {
        **os.environ,
        "HOME": str(home),
        "SECOPSAI_CORE_SYNC_CONFIG_FILE": str(config),
        "SECOPSAI_CORE_SYNC_CREDENTIALS_FILE": str(credentials),
        "SECOPSAI_CORE_SYNC_LOCK_FILE": str(lock),
    }

    result = subprocess.run(
        [
            str(EDGE),
            "core",
            "sync-service",
            "install",
            "--core-root",
            str(core),
            "--output",
            str(output),
            "--interval",
            "120",
            "--access-token",
            "scoped-core-export-token",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    assert stat.S_IMODE(credentials.stat().st_mode) == 0o600
    payload = json.loads(config.read_text())
    assert payload == {
        "core_root": str(core),
        "db_path": "",
        "interval": 120,
        "output": str(output),
        "profile": "local",
    }
    assert json.loads(credentials.read_text()) == {
        "access_token": "scoped-core-export-token",
        "api_url": "http://127.0.0.1:8000",
    }

    if sys.platform == "darwin":
        plist_path = home / "Library" / "LaunchAgents" / "ai.secopsai.edge-core-sync.plist"
        with plist_path.open("rb") as handle:
            service = plistlib.load(handle)
        assert service["StartInterval"] == 120
        assert service["RunAtLoad"] is True
        assert service["ProgramArguments"][0].endswith("core-sync-runner.py")
        assert service["ProgramArguments"][1:] == [
            "--config", str(config), "--credentials", str(credentials), "--lock", str(lock)
        ]
        assert str(ROOT) not in service["ProgramArguments"][0]
        assert "KeepAlive" not in service
    else:
        timer = (home / ".config" / "systemd" / "user" / "ai.secopsai.edge-core-sync.timer").read_text()
        service = (home / ".config" / "systemd" / "user" / "ai.secopsai.edge-core-sync.service").read_text()
        assert "OnUnitActiveSec=120" in timer
        assert "Type=oneshot" in service
        assert "core-sync-runner.py" in service


def test_core_sync_service_rejects_unsafe_interval(tmp_path: Path) -> None:
    core = tmp_path / "core"
    core.mkdir()
    result = subprocess.run(
        [str(EDGE), "core", "sync-service", "install", "--core-root", str(core), "--interval", "10"],
        cwd=ROOT,
        env={**os.environ, "HOME": str(tmp_path)},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "between 60 and 86400" in result.stderr


def test_configured_sync_invokes_core_without_exposing_credentials_and_skips_overlap(tmp_path: Path) -> None:
    core = tmp_path / "core"
    executable = core / ".venv" / "bin" / "secopsai"
    executable.parent.mkdir(parents=True)
    args_file = tmp_path / "core-args.txt"
    env_file = tmp_path / "core-env.txt"
    executable.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > "$CORE_ARGS_FILE"\nprintf "%s\\n%s\\n%s\\n" "$SECOPSAI_EDGE_API_URL" "$SECOPSAI_EDGE_ACCESS_TOKEN" "$SECOPSAI_EDGE_ADMIN_TOKEN" > "$CORE_ENV_FILE"\n'
    )
    executable.chmod(0o755)
    config = tmp_path / "config.json"
    credentials = tmp_path / "credentials.json"
    lock = tmp_path / "sync.lock"
    config.write_text(json.dumps({"profile": "cloud", "core_root": str(core), "output": "", "db_path": "", "interval": 300}))
    credentials.write_text(json.dumps({"api_url": "https://edge.example.test", "access_token": "scoped-export-token"}))
    config.chmod(0o600)
    credentials.chmod(0o600)
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "SECOPSAI_CORE_SYNC_CONFIG_FILE": str(config),
        "SECOPSAI_CORE_SYNC_CREDENTIALS_FILE": str(credentials),
        "SECOPSAI_CORE_SYNC_LOCK_FILE": str(lock),
        "CORE_ARGS_FILE": str(args_file),
        "CORE_ENV_FILE": str(env_file),
    }

    completed = subprocess.run([str(EDGE), "core", "sync-service", "run-now"], cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert args_file.read_text().splitlines() == ["edge", "sync"]
    assert env_file.read_text().splitlines() == [
        "https://edge.example.test",
        "scoped-export-token",
        "scoped-export-token",
    ]

    args_file.unlink()
    with lock.open("a+") as lock_handle:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        overlapping = subprocess.run([str(EDGE), "core", "sync-service", "run-now"], cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    assert overlapping.returncode == 0
    assert "already running" in overlapping.stderr
    assert not args_file.exists()


def test_core_push_transfers_normalized_bundle_without_secret_arguments(tmp_path: Path) -> None:
    output = tmp_path / "edge-bundle.json"
    _BridgeHandler.edge_authorization = ""
    _BridgeHandler.core_authorization = ""
    with _Server() as edge_server, _Server() as core_server:
        command = [
            str(EDGE),
            "core",
            "push",
            "--cloud",
            "--core-api-url",
            core_server.url,
            "--output",
            str(output),
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env={
                **os.environ,
                "HOME": str(tmp_path),
                "SECOPSAI_CLOUD_API_URL": edge_server.url,
                "SECOPSAI_EDGE_CORE_TOKEN": "scoped-edge-export-secret",
                "SECOPSAI_CORE_INGEST_TOKEN": "hosted-core-ingest-secret",
            },
            text=True,
            capture_output=True,
            check=False,
        )

    assert completed.returncode == 0, completed.stderr
    assert "Core import complete" in completed.stdout
    assert "scoped-edge-export-secret" not in completed.stdout + completed.stderr
    assert "hosted-core-ingest-secret" not in completed.stdout + completed.stderr
    assert all("secret" not in argument for argument in command)
    assert json.loads(output.read_text())["schema_version"] == "secopsai.edge.bundle.v1"
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert _BridgeHandler.edge_authorization == "Bearer scoped-edge-export-secret"
    assert _BridgeHandler.core_authorization == "Bearer hosted-core-ingest-secret"


def test_core_push_retries_transient_import_failure(tmp_path: Path) -> None:
    output = tmp_path / "edge-bundle.json"
    _BridgeHandler.core_failures_remaining = 1
    with _Server() as edge_server, _Server() as core_server:
        completed = subprocess.run(
            [
                str(EDGE),
                "core",
                "push",
                "--cloud",
                "--core-api-url",
                core_server.url,
                "--output",
                str(output),
            ],
            cwd=ROOT,
            env={
                **os.environ,
                "HOME": str(tmp_path),
                "SECOPSAI_CLOUD_API_URL": edge_server.url,
                "SECOPSAI_EDGE_CORE_TOKEN": "scoped-edge-export-secret",
                "SECOPSAI_CORE_INGEST_TOKEN": "hosted-core-ingest-secret",
            },
            text=True,
            capture_output=True,
            check=False,
        )

    assert completed.returncode == 0, completed.stderr
    assert "Core import complete" in completed.stdout
    assert _BridgeHandler.core_failures_remaining == 0


def test_hosted_sync_service_stores_scoped_credentials_and_needs_no_core_checkout(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    config = tmp_path / "config.json"
    credentials = tmp_path / "credentials.json"
    lock = tmp_path / "sync.lock"
    output = tmp_path / "edge-bundle.json"
    completed = subprocess.run(
        [
            str(EDGE),
            "core",
            "sync-service",
            "install",
            "--cloud",
            "--core-api-url",
            "https://core.example.test",
            "--output",
            str(output),
            "--interval",
            "600",
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "HOME": str(home),
            "SECOPSAI_CLOUD_API_URL": "https://edge.example.test",
            "SECOPSAI_EDGE_CORE_TOKEN": "scoped-edge-export-secret",
            "SECOPSAI_CORE_INGEST_TOKEN": "hosted-core-ingest-secret",
            "SECOPSAI_CORE_SYNC_CONFIG_FILE": str(config),
            "SECOPSAI_CORE_SYNC_CREDENTIALS_FILE": str(credentials),
            "SECOPSAI_CORE_SYNC_LOCK_FILE": str(lock),
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(config.read_text()) == {
        "core_root": "",
        "db_path": "",
        "destination": "hosted",
        "interval": 600,
        "output": str(output),
        "profile": "cloud",
    }
    assert json.loads(credentials.read_text()) == {
        "core_api_url": "https://core.example.test",
        "core_ingest_token": "hosted-core-ingest-secret",
        "edge_access_token": "scoped-edge-export-secret",
        "edge_api_url": "https://edge.example.test",
    }
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    assert stat.S_IMODE(credentials.stat().st_mode) == 0o600


def test_hosted_runner_rejects_plain_http_remote_endpoints(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    credentials = tmp_path / "credentials.json"
    lock = tmp_path / "sync.lock"
    config.write_text(json.dumps({"destination": "hosted", "output": ""}))
    credentials.write_text(
        json.dumps(
            {
                "edge_api_url": "http://edge.example.test",
                "edge_access_token": "edge-secret",
                "core_api_url": "https://core.example.test",
                "core_ingest_token": "core-secret",
            }
        )
    )
    config.chmod(0o600)
    credentials.chmod(0o600)

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "core-sync-runner.py"),
            "--config",
            str(config),
            "--credentials",
            str(credentials),
            "--lock",
            str(lock),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "must use HTTPS" in completed.stderr
    assert "edge-secret" not in completed.stderr
