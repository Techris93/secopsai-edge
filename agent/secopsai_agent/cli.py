from __future__ import annotations

import argparse
import json
import os
import socket
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
