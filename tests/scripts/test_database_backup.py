from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "database-backup"
REQUIRED_TABLES = (
    "organizations",
    "sites",
    "sensors",
    "assets",
    "findings",
    "reports",
    "alembic_version",
)


def executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def fake_client_environment(tmp_path: Path) -> tuple[dict[str, str], Path]:
    calls = tmp_path / "calls.log"
    executable(
        tmp_path / "psql",
        "#!/bin/sh\nprintf '160011\\n'\n",
    )
    executable(
        tmp_path / "pg_dump",
        "#!/bin/sh\nif [ \"${1:-}\" = --version ]; then printf 'pg_dump (PostgreSQL) 18.0\\n'; exit 0; fi\nexit 91\n",
    )
    table_listing = "".join(f"printf 'TABLE public {table} owner\\n'\n" for table in REQUIRED_TABLES)
    executable(
        tmp_path / "pg_restore",
        "#!/bin/sh\n"
        "if [ \"${1:-}\" = --version ]; then printf 'pg_restore (PostgreSQL) 18.0\\n'; exit 0; fi\n"
        + table_listing,
    )
    executable(
        tmp_path / "docker",
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >>\"$CALL_LOG\"\n"
        "if [ \"${1:-}\" = info ]; then exit 0; fi\n"
        "case \" $* \" in\n"
        "  *' pg_dump '*) printf 'fake-custom-archive' ;;\n"
        "  *' pg_restore '*) cat >/dev/null ;;\n"
        "esac\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    env["CALL_LOG"] = str(calls)
    return env, calls


def test_create_uses_matching_docker_client_without_leaking_url(tmp_path: Path) -> None:
    env, calls = fake_client_environment(tmp_path)
    output = tmp_path / "backup.dump"
    secret_url = "postgresql://user:top-secret@127.0.0.1:5432/secopsai_edge"

    result = subprocess.run(
        [str(SCRIPT), "create", "--database-url", secret_url, "--output", str(output)],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output.read_bytes() == b"fake-custom-archive"
    assert "postgres:16-alpine" in calls.read_text(encoding="utf-8")
    assert " pg_dump " in f" {calls.read_text(encoding='utf-8')} "
    assert "top-secret" not in result.stdout
    assert "top-secret" not in result.stderr
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_restore_uses_target_major_docker_client(tmp_path: Path) -> None:
    env, calls = fake_client_environment(tmp_path)
    archive = tmp_path / "backup.dump"
    archive.write_bytes(b"fake-custom-archive")
    secret_url = "postgresql://user:top-secret@127.0.0.1:5432/restore_target"

    result = subprocess.run(
        [
            str(SCRIPT),
            "restore",
            "--input",
            str(archive),
            "--target-url",
            secret_url,
            "--confirm-database",
            "restore_target",
        ],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "postgres:16-alpine" in calls.read_text(encoding="utf-8")
    assert " pg_restore " in f" {calls.read_text(encoding='utf-8')} "
    assert "top-secret" not in result.stdout
    assert "top-secret" not in result.stderr
