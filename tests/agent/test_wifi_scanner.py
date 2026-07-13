from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from secopsai_agent.wifi_scanner import (
    LinuxIwWifiScanner,
    MacOSWifiScanner,
    UnsupportedWifiScanner,
    WifiScanUnavailable,
    create_wifi_scanner,
    parse_airport_scan,
    parse_iw_interfaces,
    parse_iw_scan,
)


AIRPORT_OUTPUT = """SSID BSSID             RSSI CHANNEL HT CC SECURITY (auth/unicast/group)
Office WiFi 00:11:22:33:44:55 -48 6 Y US WPA2(PSK/AES/AES)
"""

IW_OUTPUT = """BSS 00:11:22:33:44:55(on wlan1)
\tfreq: 2437
\tsignal: -48.00 dBm
\tcapability: ESS Privacy ShortSlotTime (0x0411)
\tSSID: Office WiFi
\tRSN:
\t\t* Version: 1
\t\t* Authentication suites: PSK
BSS 66:77:88:99:aa:bb(on wlan1)
\tfreq: 5180
\tsignal: -62.40 dBm
\tcapability: ESS (0x0001)
\tSSID:
"""


def test_airport_parser_records_dbm_and_backend() -> None:
    networks = parse_airport_scan(AIRPORT_OUTPUT)

    assert len(networks) == 1
    assert networks[0].ssid == "Office WiFi"
    assert networks[0].signal == -48
    assert networks[0].source == "macos:airport"


def test_iw_parser_normalizes_networks_channels_and_encryption() -> None:
    networks = parse_iw_scan(IW_OUTPUT, interface="wlan1")

    assert [(item.ssid, item.channel, item.signal, item.encryption) for item in networks] == [
        ("Office WiFi", 6, -48, "WPA2"),
        ("<hidden>", 36, -62, "Open"),
    ]
    assert {item.source for item in networks} == {"linux:iw:wlan1"}


def test_iw_interface_parser_preserves_first_seen_order() -> None:
    output = """phy#1
\tInterface wlan1
\t\ttype managed
phy#0
\tInterface wlan0
\t\ttype managed
\tInterface wlan1
"""
    assert parse_iw_interfaces(output) == ["wlan1", "wlan0"]


def test_linux_capability_explains_missing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("secopsai_agent.wifi_scanner.shutil.which", lambda _: None)

    capability = LinuxIwWifiScanner(interface="wlan1").capability()

    assert capability.supported is False
    assert capability.requires_elevated_permission is True
    assert "requires the 'iw' package" in capability.reason


def test_linux_permission_failure_is_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("secopsai_agent.wifi_scanner.shutil.which", lambda _: "/usr/sbin/iw")
    monkeypatch.setattr(
        "secopsai_agent.wifi_scanner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="command failed: Operation not permitted (-1)",
        ),
    )

    with pytest.raises(WifiScanUnavailable, match="CAP_NET_ADMIN"):
        LinuxIwWifiScanner(interface="wlan1").scan()


def test_linux_scan_uses_explicit_interface(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr("secopsai_agent.wifi_scanner.shutil.which", lambda _: "/usr/sbin/iw")

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=IW_OUTPUT, stderr="")

    monkeypatch.setattr("secopsai_agent.wifi_scanner.subprocess.run", run)
    networks = LinuxIwWifiScanner(interface="wlan1").scan()

    assert calls == [["/usr/sbin/iw", "dev", "wlan1", "scan"]]
    assert len(networks) == 2


def test_platform_selection_never_falls_back_silently() -> None:
    assert isinstance(create_wifi_scanner(platform_name="darwin"), MacOSWifiScanner)
    assert isinstance(create_wifi_scanner(platform_name="linux"), LinuxIwWifiScanner)
    unsupported = create_wifi_scanner(platform_name="win32")
    assert isinstance(unsupported, UnsupportedWifiScanner)
    with pytest.raises(WifiScanUnavailable, match="not supported"):
        unsupported.scan()
