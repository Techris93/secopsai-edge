from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from secopsai_agent.models import AssetObservation
from secopsai_agent.nmap_parser import parse_nmap_xml
from secopsai_agent.safety import ScanSafetyPolicy, validate_target_cidr


DEFAULT_RISK_PORTS = [22, 23, 80, 443, 445, 3306, 5432, 5900, 6379, 3389, 9200]


@dataclass(slots=True)
class NmapScanConfig:
    target_cidr: str
    ports: list[int] = field(default_factory=lambda: DEFAULT_RISK_PORTS.copy())
    timeout_seconds: int = 30
    safety_policy: ScanSafetyPolicy = field(default_factory=ScanSafetyPolicy)


class NmapScanner:
    def __init__(self, nmap_path: str | None = None) -> None:
        self.nmap_path = nmap_path or shutil.which("nmap")
        if not self.nmap_path:
            raise RuntimeError("nmap is required but was not found on PATH.")

    def preview(self, config: NmapScanConfig) -> dict[str, object]:
        target = validate_target_cidr(config.target_cidr, config.safety_policy)
        return {
            "target_cidr": target,
            "ports": config.ports,
            "discovery_command": self._discovery_command(target, config.timeout_seconds),
            "service_command": self._service_command(target, config.ports, config.timeout_seconds),
        }

    def discover(self, config: NmapScanConfig) -> list[AssetObservation]:
        target = validate_target_cidr(config.target_cidr, config.safety_policy)
        discovery_xml = self._run(self._discovery_command(target, config.timeout_seconds))
        discovered = parse_nmap_xml(discovery_xml)

        if not discovered:
            return []

        service_xml = self._run(self._service_command(target, config.ports, config.timeout_seconds))
        by_ip = {asset.ip: asset for asset in discovered}
        for asset in parse_nmap_xml(service_xml):
            if asset.ip in by_ip:
                by_ip[asset.ip].services = asset.services
            else:
                by_ip[asset.ip] = asset
        return list(by_ip.values())

    def _run(self, command: list[str]) -> str:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout

    def _discovery_command(self, target: str, timeout_seconds: int) -> list[str]:
        return [
            self.nmap_path,
            "-oX",
            "-",
            "-sn",
            "-T2",
            "--max-retries",
            "2",
            "--host-timeout",
            f"{timeout_seconds}s",
            target,
        ]

    def _service_command(self, target: str, ports: list[int], timeout_seconds: int) -> list[str]:
        port_list = ",".join(str(port) for port in ports)
        return [
            self.nmap_path,
            "-oX",
            "-",
            "-sV",
            "--version-light",
            "-T2",
            "--max-retries",
            "2",
            "--host-timeout",
            f"{timeout_seconds}s",
            "-p",
            port_list,
            target,
        ]
