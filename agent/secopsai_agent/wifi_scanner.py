from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Protocol

from secopsai_agent.models import WifiNetworkObservation


AIRPORT_PATH = (
    "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
)


class WifiScanUnavailable(RuntimeError):
    """Raised when Wi-Fi collection was requested but cannot run truthfully."""


@dataclass(frozen=True, slots=True)
class WifiCapability:
    platform: str
    supported: bool
    backend: str | None
    interface: str | None
    signal_unit: str
    reason: str
    requires_elevated_permission: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class WifiScanner(Protocol):
    def capability(self) -> WifiCapability: ...

    def scan(self) -> list[WifiNetworkObservation]: ...


def parse_airport_scan(output: str) -> list[WifiNetworkObservation]:
    networks: list[WifiNetworkObservation] = []
    for line in output.splitlines()[1:]:
        if not line.strip():
            continue
        match = re.match(
            r"^(?P<ssid>.+?)\s+(?P<bssid>[0-9a-fA-F:]{17})\s+"
            r"(?P<rssi>-?\d+)\s+(?P<channel>[\d,+-]+)\s+"
            r"(?P<ht>\S+)\s+(?P<cc>\S+)\s+(?P<security>.+)$",
            line.strip(),
        )
        if not match:
            continue
        channel_text = match.group("channel").split(",", maxsplit=1)[0]
        networks.append(
            WifiNetworkObservation(
                ssid=match.group("ssid").strip(),
                bssid=match.group("bssid").lower(),
                signal=int(match.group("rssi")),
                channel=int(channel_text),
                encryption=match.group("security").strip(),
                source="macos:airport",
            )
        )
    return networks


def parse_iw_scan(output: str, *, interface: str) -> list[WifiNetworkObservation]:
    networks: list[WifiNetworkObservation] = []
    blocks = re.split(r"(?m)^BSS\s+", output)
    for block in blocks[1:]:
        header, _, body = block.partition("\n")
        bssid_match = re.match(r"(?P<bssid>[0-9a-fA-F:]{17})(?:\(on\s+[^)]+\))?", header.strip())
        if not bssid_match:
            continue
        ssid_match = re.search(r"(?m)^\s*SSID:\s*(.*)$", body)
        signal_match = re.search(r"(?m)^\s*signal:\s*(-?\d+(?:\.\d+)?)\s+dBm", body)
        frequency_match = re.search(r"(?m)^\s*freq:\s*(\d+)$", body)
        capability_match = re.search(r"(?m)^\s*capability:\s*(.*)$", body)
        ssid = (ssid_match.group(1).strip() if ssid_match else "") or "<hidden>"
        frequency = int(frequency_match.group(1)) if frequency_match else None
        signal = round(float(signal_match.group(1))) if signal_match else None
        networks.append(
            WifiNetworkObservation(
                ssid=ssid,
                bssid=bssid_match.group("bssid").lower(),
                channel=_frequency_to_channel(frequency),
                signal=signal,
                encryption=_iw_encryption(body, capability_match.group(1) if capability_match else ""),
                source=f"linux:iw:{interface}",
            )
        )
    return networks


def parse_iw_interfaces(output: str) -> list[str]:
    interfaces: list[str] = []
    for match in re.finditer(r"(?m)^\s*Interface\s+([^\s]+)\s*$", output):
        interface = match.group(1).strip()
        if interface and interface not in interfaces:
            interfaces.append(interface)
    return interfaces


class MacOSWifiScanner:
    def __init__(self, airport_path: str = AIRPORT_PATH) -> None:
        self.airport_path = airport_path

    def capability(self) -> WifiCapability:
        available = bool(shutil.which(self.airport_path) or self._airport_exists())
        return WifiCapability(
            platform="macos",
            supported=available,
            backend="airport" if available else None,
            interface=None,
            signal_unit="dBm",
            reason=(
                "Legacy macOS airport inventory is available. Monitor mode is not used."
                if available
                else "The legacy macOS airport scanner is unavailable; use Ethernet discovery or a supported Linux sensor."
            ),
        )

    def scan(self) -> list[WifiNetworkObservation]:
        capability = self.capability()
        if not capability.supported:
            raise WifiScanUnavailable(capability.reason)
        try:
            completed = subprocess.run(
                [self.airport_path, "-s"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise WifiScanUnavailable(f"macOS Wi-Fi inventory failed: {exc}") from exc
        return parse_airport_scan(completed.stdout)

    def _airport_exists(self) -> bool:
        try:
            with open(self.airport_path, "rb"):
                return True
        except OSError:
            return False


class LinuxIwWifiScanner:
    def __init__(self, interface: str | None = None, iw_path: str = "iw") -> None:
        self.interface = (interface or os.getenv("SECOPSAI_WIFI_INTERFACE") or "").strip() or None
        self.iw_path = iw_path

    def capability(self) -> WifiCapability:
        executable = shutil.which(self.iw_path)
        if executable is None:
            return WifiCapability(
                platform="linux",
                supported=False,
                backend=None,
                interface=self.interface,
                signal_unit="dBm",
                reason="Linux Wi-Fi inventory requires the 'iw' package.",
                requires_elevated_permission=True,
            )
        interface = self.interface or self._discover_interface(executable)
        if not interface:
            return WifiCapability(
                platform="linux",
                supported=False,
                backend="iw",
                interface=None,
                signal_unit="dBm",
                reason="No Linux wireless interface was found. Set SECOPSAI_WIFI_INTERFACE after attaching the adapter.",
                requires_elevated_permission=True,
            )
        return WifiCapability(
            platform="linux",
            supported=True,
            backend="iw",
            interface=interface,
            signal_unit="dBm",
            reason="Linux managed-mode inventory is available; monitor mode and packet capture are not used.",
            requires_elevated_permission=True,
        )

    def scan(self) -> list[WifiNetworkObservation]:
        capability = self.capability()
        if not capability.supported or not capability.interface:
            raise WifiScanUnavailable(capability.reason)
        executable = shutil.which(self.iw_path) or self.iw_path
        completed = subprocess.run(
            [executable, "dev", capability.interface, "scan"],
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "unknown iw error").strip()
            if "Operation not permitted" in detail or "Permission denied" in detail:
                detail = (
                    "Wi-Fi scanning needs CAP_NET_ADMIN or an approved elevated service configuration; "
                    "do not run an unreviewed installer as root."
                )
            raise WifiScanUnavailable(f"Linux Wi-Fi inventory failed on {capability.interface}: {detail}")
        return parse_iw_scan(completed.stdout, interface=capability.interface)

    def _discover_interface(self, executable: str) -> str | None:
        try:
            completed = subprocess.run(
                [executable, "dev"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        interfaces = parse_iw_interfaces(completed.stdout) if completed.returncode == 0 else []
        return interfaces[0] if interfaces else None


class UnsupportedWifiScanner:
    def __init__(self, platform_name: str) -> None:
        self.platform_name = platform_name

    def capability(self) -> WifiCapability:
        return WifiCapability(
            platform=self.platform_name,
            supported=False,
            backend=None,
            interface=None,
            signal_unit="dBm",
            reason=f"Wi-Fi inventory is not supported on platform '{self.platform_name}'.",
        )

    def scan(self) -> list[WifiNetworkObservation]:
        raise WifiScanUnavailable(self.capability().reason)


def create_wifi_scanner(
    *,
    platform_name: str | None = None,
    interface: str | None = None,
) -> WifiScanner:
    current = (platform_name or sys.platform).lower()
    if current == "darwin":
        return MacOSWifiScanner()
    if current.startswith("linux"):
        return LinuxIwWifiScanner(interface=interface)
    return UnsupportedWifiScanner(current)


def wifi_capability(
    *,
    platform_name: str | None = None,
    interface: str | None = None,
) -> WifiCapability:
    return create_wifi_scanner(platform_name=platform_name, interface=interface).capability()


def _iw_encryption(body: str, capabilities: str) -> str:
    upper = body.upper()
    if "SAE" in upper or "OWE" in upper:
        return "WPA3"
    if re.search(r"(?m)^\s*RSN:", body):
        return "WPA2"
    if re.search(r"(?m)^\s*WPA:", body):
        return "WPA"
    if "PRIVACY" in capabilities.upper():
        return "WEP"
    return "Open"


def _frequency_to_channel(frequency: int | None) -> int | None:
    if frequency is None:
        return None
    if frequency == 2484:
        return 14
    if 2412 <= frequency <= 2472:
        return (frequency - 2407) // 5
    if 5000 <= frequency <= 5895:
        return (frequency - 5000) // 5
    if 5955 <= frequency <= 7115:
        return (frequency - 5950) // 5
    return None
