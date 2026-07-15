#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit

DEFAULT_DASHBOARD_URL = "https://secopsai-dashboard.pages.dev"


def _safe_url(url: str) -> str:
    """Remove credentials and query material before writing an evidence record."""
    parts = urlsplit(url)
    hostname = parts.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname
    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def _error_code(error: BaseException) -> str:
    if isinstance(error, urllib.error.HTTPError):
        return "http_error"
    if isinstance(error, urllib.error.URLError):
        reason = error.reason
        if isinstance(reason, socket.gaierror):
            return "dns_resolution_failed"
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return "network_timeout"
        return "network_error"
    if isinstance(error, (TimeoutError, socket.timeout)):
        return "network_timeout"
    if isinstance(error, json.JSONDecodeError):
        return "invalid_json"
    return "check_failed"


def check(
    url: str,
    *,
    expect_json_status: str | None = None,
    expect_text: str | None = None,
    expect_json: bool = False,
    headers: Mapping[str, str] | None = None,
) -> dict[str, object]:
    started = time.monotonic()
    try:
        request_headers = {"User-Agent": "SecOpsAI-Edge-Health/1"}
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(url, headers=request_headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(1_000_000).decode("utf-8", errors="replace")
            status_code = int(response.status)
        result: dict[str, object] = {
            "url": _safe_url(url),
            "ok": 200 <= status_code < 300,
            "status_code": status_code,
            "latency_ms": round((time.monotonic() - started) * 1000),
        }
        if expect_json_status:
            payload = json.loads(body)
            result["reported_status"] = payload.get("status")
            result["version"] = payload.get("version")
            result["commit"] = payload.get("commit")
            result["schema_revision"] = payload.get("schema_revision")
            result["ok"] = bool(result["ok"] and payload.get("status") == expect_json_status)
        elif expect_json:
            json.loads(body)
            result["json_valid"] = True
        if expect_text:
            result["expected_content"] = expect_text
            result["ok"] = bool(result["ok"] and expect_text in body)
        return result
    except urllib.error.HTTPError as exc:
        return {
            "url": _safe_url(url),
            "ok": False,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "error": type(exc).__name__,
            "error_code": _error_code(exc),
            "status_code": int(exc.code),
        }
    except (urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as exc:
        return {
            "url": _safe_url(url),
            "ok": False,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "error": type(exc).__name__,
            "error_code": _error_code(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record non-secret SecOpsAI Edge hosted health evidence")
    parser.add_argument("--api-url", default="https://secopsai-edge-api.onrender.com")
    parser.add_argument("--dashboard-url", default=DEFAULT_DASHBOARD_URL)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    dashboard_url = args.dashboard_url.rstrip("/")
    evidence = {
        "schema_version": "secopsai.edge.hosted-health.v1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": [
            check(f"{api_url}/healthz", expect_json_status="ok"),
            check(f"{api_url}/readyz", expect_json_status="ready"),
            check(dashboard_url, expect_text="SecOpsAI Edge"),
        ],
    }
    evidence["ok"] = all(item["ok"] for item in evidence["checks"])
    line = json.dumps(evidence, separators=(",", ":"), sort_keys=True)
    print(line)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")
    return 0 if evidence["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
