#!/usr/bin/env python3
"""Private psql shim used by render-postgres-backup to receive Render's URL."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    major = os.environ.get("SECOPSAI_RENDER_POSTGRES_MAJOR", "")
    if sys.argv[1:] == ["--version"]:
        print(f"psql (PostgreSQL) {major or '16'}.0")
        return 0

    output_value = os.environ.get("SECOPSAI_RENDER_BACKUP_OUTPUT", "")
    database_url = next(
        (argument for argument in sys.argv[1:] if argument.startswith(("postgres://", "postgresql://"))),
        "",
    )
    if not major.isdigit() or not output_value or not database_url:
        print("Render backup proxy received incomplete connection metadata.", file=sys.stderr)
        return 2

    output = Path(output_value).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "docker",
        "run",
        "--rm",
        f"postgres:{major}-alpine",
        "pg_dump",
        "--format=custom",
        "--compress=9",
        "--no-owner",
        "--no-acl",
        database_url,
    ]
    try:
        with output.open("wb") as archive:
            result = subprocess.run(command, stdout=archive, stderr=subprocess.PIPE, check=False)
    except (OSError, subprocess.SubprocessError):
        output.unlink(missing_ok=True)
        print("Render PostgreSQL backup could not start.", file=sys.stderr)
        return 2
    if result.returncode != 0:
        output.unlink(missing_ok=True)
        print("Render PostgreSQL backup failed; connection details were withheld.", file=sys.stderr)
        return result.returncode or 1
    output.chmod(0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
