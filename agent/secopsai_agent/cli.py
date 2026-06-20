from __future__ import annotations

import argparse
import json
import os
import socket
import time
from dataclasses import asdict

from secopsai_agent.api_client import SecOpsApiClient
from secopsai_agent.models import ScanResult
from secopsai_agent.network_scanner import NmapScanConfig, NmapScanner
from secopsai_agent.wifi_scanner import MacOSWifiScanner


def main() -> int:
    parser = argparse.ArgumentParser(prog="secopsai-agent")
    subcommands = parser.add_subparsers(dest="command", required=True)

    preview = subcommands.add_parser("preview", help="Show the safe Nmap commands for a target.")
    preview.add_argument("target_cidr")

    scan = subcommands.add_parser("scan", help="Run a local scan and print normalized JSON.")
    scan.add_argument("target_cidr")
    scan.add_argument("--sensor-id", default=os.getenv("SECOPSAI_SENSOR_ID", "local-sensor"))
    scan.add_argument("--include-wifi", action="store_true")

    submit = subcommands.add_parser("submit", help="Run a scan and submit it to the API.")
    submit.add_argument("target_cidr")
    submit.add_argument("--sensor-id", default=os.getenv("SECOPSAI_SENSOR_ID"))
    submit.add_argument("--api-url", default=os.getenv("SECOPSAI_API_URL", "http://127.0.0.1:8000"))
    submit.add_argument("--sensor-token", default=os.getenv("SECOPSAI_SENSOR_TOKEN"))
    submit.add_argument("--include-wifi", action="store_true")

    worker = subcommands.add_parser("worker", help="Poll the API for remote scan jobs and run them locally.")
    worker.add_argument("--sensor-id", default=os.getenv("SECOPSAI_SENSOR_ID"))
    worker.add_argument("--api-url", default=os.getenv("SECOPSAI_API_URL", "http://127.0.0.1:8000"))
    worker.add_argument("--sensor-token", default=os.getenv("SECOPSAI_SENSOR_TOKEN"))
    worker.add_argument("--poll-interval", type=float, default=30.0)
    worker.add_argument("--once", action="store_true")

    args = parser.parse_args()
    scanner = NmapScanner()

    if args.command == "preview":
        print(json.dumps(scanner.preview(NmapScanConfig(args.target_cidr)), indent=2))
        return 0

    if args.command == "scan":
        result = _run_scan(scanner, args.target_cidr, args.sensor_id, args.include_wifi)
        print(json.dumps(_scan_to_json(result), indent=2))
        return 0

    if args.command == "submit":
        if not args.sensor_id or not args.sensor_token:
            parser.error("submit requires --sensor-id and --sensor-token or matching environment vars.")
        result = _run_scan(scanner, args.target_cidr, args.sensor_id, args.include_wifi)
        response = SecOpsApiClient(args.api_url, args.sensor_token).submit_scan(result)
        print(json.dumps(response, indent=2))
        return 0

    if args.command == "worker":
        if not args.sensor_id or not args.sensor_token:
            parser.error("worker requires --sensor-id and --sensor-token or matching environment vars.")
        return _run_worker(
            scanner=scanner,
            api_url=args.api_url,
            sensor_id=args.sensor_id,
            sensor_token=args.sensor_token,
            poll_interval=args.poll_interval,
            once=args.once,
        )

    return 1


def _run_scan(
    scanner: NmapScanner,
    target_cidr: str,
    sensor_id: str,
    include_wifi: bool,
) -> ScanResult:
    result = ScanResult(
        sensor_id=sensor_id,
        target_cidr=target_cidr,
        scan_source=f"macos:{socket.gethostname()}",
    )
    result.assets = scanner.discover(NmapScanConfig(target_cidr=target_cidr))
    if include_wifi:
        result.wifi_networks = MacOSWifiScanner().scan()
    return result.complete()


def _run_worker(
    scanner: NmapScanner,
    api_url: str,
    sensor_id: str,
    sensor_token: str,
    poll_interval: float,
    once: bool,
) -> int:
    client = SecOpsApiClient(api_url, sensor_token, timeout=30.0)
    while True:
        job = client.claim_scan_job(sensor_id)
        if not job:
            if once:
                print(json.dumps({"status": "idle", "message": "No queued scan jobs."}, indent=2))
                return 0
            time.sleep(max(poll_interval, 1.0))
            continue

        job_id = str(job["id"])
        try:
            target_cidr = str(job["target_cidr"])
            include_wifi = bool(job.get("include_wifi"))
            preview = scanner.preview(NmapScanConfig(target_cidr))
            client.start_scan_job(sensor_id, job_id, preview)
            result = _run_scan(scanner, target_cidr, sensor_id, include_wifi)
            result.scan_job_id = job_id
            response = client.submit_scan(result)
            print(
                json.dumps(
                    {"status": "completed", "job_id": job_id, "scan": response},
                    indent=2,
                )
            )
            if once:
                return 0
        except Exception as exc:
            _fail_job(client, sensor_id, job_id, exc)
            if once:
                return 1


def _fail_job(client: SecOpsApiClient, sensor_id: str, job_id: str, exc: Exception) -> None:
    error = f"{type(exc).__name__}: {exc}"
    try:
        client.fail_scan_job(sensor_id, job_id, error)
    finally:
        print(json.dumps({"status": "failed", "job_id": job_id, "error": error}, indent=2))


def _scan_to_json(scan: ScanResult) -> dict[str, object]:
    def convert(value: object) -> object:
        if hasattr(value, "isoformat"):
            return value.isoformat()  # type: ignore[union-attr]
        if isinstance(value, list):
            return [convert(item) for item in value]
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        return value

    return convert(asdict(scan))  # type: ignore[return-value]


if __name__ == "__main__":
    raise SystemExit(main())
