from __future__ import annotations

import json
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


def test_core_sync_service_installer_generates_supervised_timer(tmp_path: Path) -> None:
    home = tmp_path / "home"
    core = tmp_path / "core"
    output = tmp_path / "edge-bundle.json"
    config = tmp_path / "core-sync.json"
    lock = tmp_path / "core-sync.lock"
    home.mkdir()
    core.mkdir()
    env = {
        **os.environ,
        "HOME": str(home),
        "SECOPSAI_CORE_SYNC_CONFIG_FILE": str(config),
        "SECOPSAI_CORE_SYNC_LOCK_DIR": str(lock),
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
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    payload = json.loads(config.read_text())
    assert payload == {
        "core_root": str(core),
        "db_path": "",
        "interval": 120,
        "output": str(output),
        "profile": "local",
    }

    if sys.platform == "darwin":
        plist_path = home / "Library" / "LaunchAgents" / "ai.secopsai.edge-core-sync.plist"
        with plist_path.open("rb") as handle:
            service = plistlib.load(handle)
        assert service["StartInterval"] == 120
        assert service["RunAtLoad"] is True
        assert service["ProgramArguments"][-3:] == ["core", "sync-service", "run-configured"]
        assert "KeepAlive" not in service
    else:
        timer = (home / ".config" / "systemd" / "user" / "ai.secopsai.edge-core-sync.timer").read_text()
        service = (home / ".config" / "systemd" / "user" / "ai.secopsai.edge-core-sync.service").read_text()
        assert "OnUnitActiveSec=120" in timer
        assert "Type=oneshot" in service
        assert "core sync-service run-configured" in service


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


def test_configured_sync_exports_imports_and_skips_overlap(tmp_path: Path) -> None:
    requests: list[tuple[str, str | None]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            requests.append((self.path, self.headers.get("Authorization")))
            body = b'{"schema_version":"secopsai.edge.bundle.v1","graph":{"nodes":[],"edges":[]},"findings":[]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        core = tmp_path / "core"
        python = core / ".venv" / "bin" / "python"
        python.parent.mkdir(parents=True)
        args_file = tmp_path / "core-args.txt"
        python.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CORE_ARGS_FILE"\n')
        python.chmod(0o755)
        bundle = tmp_path / "bundle.json"
        config = tmp_path / "config.json"
        lock = tmp_path / "sync.lock"
        config.write_text(json.dumps({
            "profile": "cloud",
            "core_root": str(core),
            "output": str(bundle),
            "db_path": "",
            "interval": 300,
        }))
        env = {
            **os.environ,
            "SECOPSAI_CORE_SYNC_CONFIG_FILE": str(config),
            "SECOPSAI_CORE_SYNC_LOCK_DIR": str(lock),
            "SECOPSAI_CLOUD_API_URL": f"http://127.0.0.1:{server.server_port}",
            "SECOPSAI_CLOUD_ADMIN_TOKEN": "test-admin-token",
            "CORE_ARGS_FILE": str(args_file),
        }

        completed = subprocess.run(
            [str(EDGE), "core", "sync-service", "run-now"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert json.loads(bundle.read_text())["schema_version"] == "secopsai.edge.bundle.v1"
        assert args_file.read_text().splitlines() == [
            "-m", "secopsai.cli", "edge", "import", "--bundle", str(bundle)
        ]
        assert requests == [("/api/v1/core/export", "Bearer test-admin-token")]
        assert not lock.exists()

        lock.mkdir()
        (lock / "pid").write_text(str(os.getpid()))
        args_file.unlink()
        overlapping = subprocess.run(
            [str(EDGE), "core", "sync-service", "run-now"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert overlapping.returncode == 0
        assert "already running" in overlapping.stderr
        assert not args_file.exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
