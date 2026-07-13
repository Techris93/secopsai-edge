#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import stat
import subprocess
import sys
from pathlib import Path


def read_protected_json(path: Path) -> dict[str, object]:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise RuntimeError(f"{path} must not be accessible by group or other users")
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize SecOpsAI Edge into the local Core store")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    args = parser.parse_args()

    config = read_protected_json(args.config)
    credentials = read_protected_json(args.credentials)
    core_root = Path(str(config.get("core_root", ""))).expanduser().resolve()
    if not core_root.is_dir():
        raise RuntimeError(f"SecOpsAI Core root not found: {core_root}")
    api_url = str(credentials.get("api_url", "")).rstrip("/")
    access_token = str(credentials.get("access_token") or credentials.get("admin_token") or "")
    if not api_url or not access_token:
        raise RuntimeError("Core sync API URL and access token are required")

    args.lock.parent.mkdir(parents=True, exist_ok=True)
    with args.lock.open("a+") as lock_handle:
        try:
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Core synchronization is already running; skipped overlapping run", file=sys.stderr)
            return 0

        executable = core_root / ".venv" / "bin" / "secopsai"
        if executable.is_file() and os.access(executable, os.X_OK):
            command = [str(executable), "edge", "sync"]
        else:
            python = core_root / ".venv" / "bin" / "python"
            if not python.is_file():
                raise RuntimeError(f"Core virtual environment not found under {core_root / '.venv'}")
            command = [str(python), "-m", "secopsai.cli", "edge", "sync"]
        db_path = str(config.get("db_path", ""))
        if db_path:
            command.extend(["--db-path", db_path])

        env = os.environ.copy()
        env["SECOPSAI_EDGE_API_URL"] = api_url
        env["SECOPSAI_EDGE_ACCESS_TOKEN"] = access_token
        env["SECOPSAI_EDGE_ADMIN_TOKEN"] = access_token
        completed = subprocess.run(command, cwd=core_root, env=env, check=False)
        return completed.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Core synchronization failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
