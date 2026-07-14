#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import ipaddress
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_BUNDLE_BYTES = 10 * 1024 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
CORE_IMPORT_ATTEMPTS = 3
CORE_RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
CORE_RETRY_BACKOFF_SECONDS = 0.5


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def read_protected_json(path: Path) -> dict[str, object]:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise RuntimeError(f"{path} must not be accessible by group or other users")
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return payload


def validate_api_url(value: str, label: str) -> str:
    base_url = value.rstrip("/")
    if any(ord(character) < 32 or ord(character) == 127 for character in base_url):
        raise RuntimeError(f"{label} URL contains an invalid control character")
    parsed = urlparse(base_url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError(f"{label} URL must not contain credentials, a query, or a fragment")
    if not parsed.hostname or parsed.scheme not in {"http", "https"}:
        raise RuntimeError(f"{label} URL must be an absolute HTTP(S) URL")
    if parsed.scheme == "http" and not is_loopback_host(parsed.hostname):
        raise RuntimeError(f"{label} URL must use HTTPS unless it is loopback-only")
    return base_url


def is_loopback_host(hostname: str) -> bool:
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def bounded_request(
    *,
    url: str,
    token: str,
    method: str,
    label: str,
    body: bytes | None = None,
    max_bytes: int,
    retry_attempts: int = 1,
) -> bytes:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "SecOpsAI-Edge-Core-Bridge/1",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    attempts = max(1, retry_attempts)
    for attempt in range(attempts):
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with build_opener(NoRedirectHandler()).open(request, timeout=30) as response:
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > max_bytes:
                    raise RuntimeError(f"{label} response exceeds the {max_bytes}-byte limit")
                payload = response.read(max_bytes + 1)
        except HTTPError as exc:
            if exc.code in CORE_RETRYABLE_STATUS_CODES and attempt < attempts - 1:
                time.sleep(CORE_RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            raise RuntimeError(f"{label} returned HTTP {exc.code}") from exc
        except URLError as exc:
            if attempt < attempts - 1:
                time.sleep(CORE_RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            raise RuntimeError(f"{label} request failed: {exc.reason}") from exc
        if len(payload) > max_bytes:
            raise RuntimeError(f"{label} response exceeds the {max_bytes}-byte limit")
        return payload
    raise RuntimeError(f"{label} request failed after {attempts} attempts")


def push_to_hosted_core(config: dict[str, object], credentials: dict[str, object]) -> int:
    edge_api_url = validate_api_url(
        str(credentials.get("edge_api_url") or credentials.get("api_url") or ""),
        "Edge API",
    )
    edge_access_token = str(
        credentials.get("edge_access_token")
        or credentials.get("access_token")
        or credentials.get("admin_token")
        or ""
    )
    core_api_url = validate_api_url(str(credentials.get("core_api_url") or ""), "Core API")
    core_ingest_token = str(credentials.get("core_ingest_token") or "")
    if not edge_access_token or not core_ingest_token:
        raise RuntimeError("Edge export and Core ingest credentials are required")

    bundle_bytes = bounded_request(
        url=f"{edge_api_url}/api/v1/core/export",
        token=edge_access_token,
        method="GET",
        label="Edge export",
        max_bytes=MAX_BUNDLE_BYTES,
    )
    try:
        bundle = json.loads(bundle_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Edge export returned invalid JSON") from exc
    if not isinstance(bundle, dict) or bundle.get("schema_version") != "secopsai.edge.bundle.v1":
        raise RuntimeError("Edge export returned an unsupported bundle")

    output = str(config.get("output") or "")
    if output:
        output_path = Path(output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=output_path.parent,
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(bundle_bytes)
                temporary = Path(handle.name)
            temporary.chmod(0o600)
            temporary.replace(output_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    response_bytes = bounded_request(
        url=f"{core_api_url}/api/v1/edge/bundles",
        token=core_ingest_token,
        method="POST",
        label="Core import",
        body=bundle_bytes,
        max_bytes=MAX_RESPONSE_BYTES,
        retry_attempts=CORE_IMPORT_ATTEMPTS,
    )
    try:
        response = json.loads(response_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Core import returned invalid JSON") from exc
    if not isinstance(response, dict) or response.get("status") != "imported":
        raise RuntimeError("Core import did not confirm the bundle")
    counts = response.get("counts") if isinstance(response.get("counts"), dict) else {}
    print(
        "Core import complete: "
        f"nodes={counts.get('nodes', 0)} edges={counts.get('edges', 0)} "
        f"findings={counts.get('findings', 0)}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize SecOpsAI Edge into Core")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    args = parser.parse_args()

    config = read_protected_json(args.config)
    credentials = read_protected_json(args.credentials)
    destination = str(config.get("destination") or "local")
    if destination not in {"local", "hosted"}:
        raise RuntimeError(f"Unsupported Core sync destination: {destination}")

    args.lock.parent.mkdir(parents=True, exist_ok=True)
    with args.lock.open("a+") as lock_handle:
        try:
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Core synchronization is already running; skipped overlapping run", file=sys.stderr)
            return 0

        if destination == "hosted":
            return push_to_hosted_core(config, credentials)

        core_root = Path(str(config.get("core_root", ""))).expanduser().resolve()
        if not core_root.is_dir():
            raise RuntimeError(f"SecOpsAI Core root not found: {core_root}")
        api_url = str(credentials.get("api_url", "")).rstrip("/")
        access_token = str(credentials.get("access_token") or credentials.get("admin_token") or "")
        if not api_url or not access_token:
            raise RuntimeError("Core sync API URL and access token are required")

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
