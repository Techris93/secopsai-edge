from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROXY = ROOT / "scripts" / "render_psql_backup_proxy.py"


def test_proxy_writes_archive_without_printing_connection_url(tmp_path: Path) -> None:
    fake_docker = tmp_path / "docker"
    fake_docker.write_text("#!/bin/sh\nprintf 'archive-bytes'\n", encoding="utf-8")
    fake_docker.chmod(0o755)
    output = tmp_path / "backup.dump"
    secret_url = "postgresql://user:top-secret@example.invalid/database"
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{tmp_path}:{env['PATH']}",
            "SECOPSAI_RENDER_POSTGRES_MAJOR": "16",
            "SECOPSAI_RENDER_BACKUP_OUTPUT": str(output),
        }
    )

    result = subprocess.run(
        [sys.executable, str(PROXY), secret_url, "-c", "SELECT 1"],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output.read_bytes() == b"archive-bytes"
    assert "top-secret" not in result.stdout
    assert "top-secret" not in result.stderr


def test_proxy_supports_render_cli_version_probe(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["SECOPSAI_RENDER_POSTGRES_MAJOR"] = "16"

    result = subprocess.run(
        [sys.executable, str(PROXY), "--version"],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "psql (PostgreSQL) 16.0"
