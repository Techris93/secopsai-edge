from __future__ import annotations

import re
import shutil
import subprocess

from secopsai_agent.models import WifiNetworkObservation


AIRPORT_PATH = (
    "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
)


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
            )
        )
    return networks


class MacOSWifiScanner:
    def __init__(self, airport_path: str = AIRPORT_PATH) -> None:
        self.airport_path = airport_path

    def scan(self) -> list[WifiNetworkObservation]:
        if not shutil.which(self.airport_path) and not self._airport_exists():
            return []
        completed = subprocess.run(
            [self.airport_path, "-s"],
            check=True,
            capture_output=True,
            text=True,
        )
        return parse_airport_scan(completed.stdout)

    def _airport_exists(self) -> bool:
        try:
            with open(self.airport_path, "rb"):
                return True
        except OSError:
            return False
