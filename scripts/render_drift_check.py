#!/usr/bin/env python3
"""Validate the deployed Render resources against the SecOpsAI Edge contract."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_REPOSITORY = "https://github.com/Techris93/secopsai-edge"
EXPECTED_POSTGRES_MAJOR = "16"
RENDER_BLUEPRINT = Path(__file__).resolve().parents[1] / "render.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check live Render service configuration without reading environment secrets."
    )
    parser.add_argument(
        "--services-json",
        type=Path,
        help="Read a saved `render services --output json` response instead of calling Render.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--expiry-warning-days",
        type=int,
        default=14,
        help="Warn when a free Render PostgreSQL database expires within this many days.",
    )
    parser.add_argument(
        "--now",
        help="UTC timestamp used for deterministic tests, for example 2026-07-13T00:00:00Z.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Return a failing exit code when operational warnings are present.",
    )
    return parser.parse_args()


def parse_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_inventory(path: Path | None) -> list[dict[str, Any]]:
    if path is not None:
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        try:
            result = subprocess.run(
                ["render", "services", "--output", "json"],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Render CLI is not installed or is not on PATH") from exc
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or "Render CLI returned a non-zero status"
            raise RuntimeError(detail) from exc
        payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise RuntimeError("Render services payload must be a JSON array")
    return payload


def validate_blueprint() -> None:
    try:
        result = subprocess.run(
            ["render", "blueprints", "validate", str(RENDER_BLUEPRINT), "--output", "json"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Render CLI is not installed or is not on PATH") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or "Render rejected render.yaml"
        raise RuntimeError(f"Blueprint validation failed: {detail}")


def normalized_repository(value: object) -> str:
    return str(value or "").strip().lower().removesuffix(".git").rstrip("/")


def auto_deploy_enabled(value: object) -> bool:
    return value is True or str(value).strip().lower() in {"yes", "true", "enabled"}


def inspect_inventory(
    inventory: list[dict[str, Any]], *, now: datetime, expiry_warning_days: int
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []

    def add(level: str, code: str, message: str) -> None:
        results.append({"level": level, "code": code, "message": message})

    service_entries = [item.get("service") for item in inventory if isinstance(item, dict)]
    service_entries = [item for item in service_entries if isinstance(item, dict)]
    postgres_entries = [item.get("postgres") for item in inventory if isinstance(item, dict)]
    postgres_entries = [item for item in postgres_entries if isinstance(item, dict)]

    def one_service(name: str) -> dict[str, Any] | None:
        matches = [item for item in service_entries if item.get("name") == name]
        if len(matches) != 1:
            add(
                "drift",
                f"{name}.count",
                f"Expected exactly one {name} service; found {len(matches)}.",
            )
            return None
        return matches[0]

    api = one_service("secopsai-edge-api")
    if api is not None:
        details = api.get("serviceDetails") if isinstance(api.get("serviceDetails"), dict) else {}
        env_details = (
            details.get("envSpecificDetails")
            if isinstance(details.get("envSpecificDetails"), dict)
            else {}
        )
        expected = {
            "type": (api.get("type"), "web_service"),
            "repository": (
                normalized_repository(api.get("repo")),
                normalized_repository(EXPECTED_REPOSITORY),
            ),
            "branch": (api.get("branch"), "main"),
            "build command": (env_details.get("buildCommand"), "pip install -r requirements.lock"),
            "start command": (env_details.get("startCommand"), "./scripts/render-start-api"),
            "health check": (details.get("healthCheckPath"), "/readyz"),
        }
        for label, (actual, wanted) in expected.items():
            if actual != wanted:
                add(
                    "drift",
                    f"api.{label.replace(' ', '_')}",
                    f"API {label} is {actual!r}; expected {wanted!r}.",
                )
        if not auto_deploy_enabled(api.get("autoDeploy")):
            add("drift", "api.auto_deploy", "API automatic deploys are disabled.")
        if not any(item["code"].startswith("api.") for item in results):
            add("ok", "api.contract", "API service matches the repository deployment contract.")

    scheduler = one_service("secopsai-edge-scheduler")
    if scheduler is not None:
        details = (
            scheduler.get("serviceDetails")
            if isinstance(scheduler.get("serviceDetails"), dict)
            else {}
        )
        env_details = (
            details.get("envSpecificDetails")
            if isinstance(details.get("envSpecificDetails"), dict)
            else {}
        )
        expected = {
            "type": (scheduler.get("type"), "cron_job"),
            "repository": (
                normalized_repository(scheduler.get("repo")),
                normalized_repository(EXPECTED_REPOSITORY),
            ),
            "branch": (scheduler.get("branch"), "main"),
            "build command": (env_details.get("buildCommand"), "pip install -r requirements.lock"),
            "start command": (env_details.get("startCommand"), "./scripts/render-run-due-schedules"),
            "schedule": (details.get("schedule"), "*/5 * * * *"),
        }
        for label, (actual, wanted) in expected.items():
            if actual != wanted:
                add(
                    "drift",
                    f"scheduler.{label.replace(' ', '_')}",
                    f"Scheduler {label} is {actual!r}; expected {wanted!r}.",
                )
        if not auto_deploy_enabled(scheduler.get("autoDeploy")):
            add("drift", "scheduler.auto_deploy", "Scheduler automatic deploys are disabled.")
        if not any(item["code"].startswith("scheduler.") for item in results):
            add("ok", "scheduler.contract", "Scheduler matches the five-minute queueing contract.")

    database_matches = [item for item in postgres_entries if item.get("name") == "secopsai-edge-postgres"]
    if len(database_matches) != 1:
        add(
            "drift",
            "database.count",
            f"Expected exactly one secopsai-edge-postgres database; found {len(database_matches)}.",
        )
    else:
        database = database_matches[0]
        if database.get("status") != "available":
            add(
                "drift",
                "database.status",
                f"Database status is {database.get('status')!r}; expected 'available'.",
            )
        if str(database.get("version")) != EXPECTED_POSTGRES_MAJOR:
            add(
                "drift",
                "database.version",
                f"Database major version is {database.get('version')!r}; expected {EXPECTED_POSTGRES_MAJOR!r}.",
            )
        if not any(item["code"].startswith("database.") for item in results):
            add("ok", "database.contract", "Database is available on the expected PostgreSQL major version.")

        if database.get("plan") == "free":
            expires_at = database.get("expiresAt")
            if not isinstance(expires_at, str) or not expires_at:
                add("warning", "database.free_plan", "Database uses the free plan and has no expiry timestamp.")
            else:
                expiry = parse_timestamp(expires_at)
                seconds_remaining = (expiry - now).total_seconds()
                days_remaining = max(0, int(seconds_remaining // 86400))
                if seconds_remaining <= 0:
                    add("drift", "database.expired", f"Free database expired at {expiry.isoformat()}.")
                elif seconds_remaining <= expiry_warning_days * 86400:
                    add(
                        "warning",
                        "database.expires_soon",
                        f"Free database expires at {expiry.isoformat()} ({days_remaining} full days remaining).",
                    )
                else:
                    add(
                        "warning",
                        "database.free_plan",
                        f"Database uses the free plan and expires at {expiry.isoformat()}.",
                    )

    return results


def main() -> int:
    args = parse_args()
    try:
        now = parse_timestamp(args.now) if args.now else datetime.now(timezone.utc)
        if args.services_json is None:
            validate_blueprint()
        results = inspect_inventory(
            load_inventory(args.services_json),
            now=now,
            expiry_warning_days=max(0, args.expiry_warning_days),
        )
        if args.services_json is None:
            results.insert(
                0,
                {
                    "level": "ok",
                    "code": "blueprint.contract",
                    "message": "render.yaml passed Render Blueprint validation.",
                },
            )
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    drift_count = sum(item["level"] == "drift" for item in results)
    warning_count = sum(item["level"] == "warning" for item in results)
    status = "drift" if drift_count else "warning" if warning_count else "ok"
    if args.json:
        print(
            json.dumps(
                {
                    "status": status,
                    "checked_at": now.isoformat(),
                    "drift_count": drift_count,
                    "warning_count": warning_count,
                    "results": results,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print("SecOpsAI Edge Render operations check")
        for item in results:
            print(f"[{item['level'].upper()}] {item['message']}")
        print(f"Result: {drift_count} drift issue(s), {warning_count} warning(s).")

    if drift_count or (args.fail_on_warning and warning_count):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
