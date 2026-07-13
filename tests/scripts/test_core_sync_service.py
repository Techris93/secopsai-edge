from __future__ import annotations

import json
import fcntl
import os
import plistlib
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EDGE = ROOT / "scripts" / "edge"


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
