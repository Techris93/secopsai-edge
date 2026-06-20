from pathlib import Path

from secopsai_agent.network_scanner import NmapScanConfig, NmapScanner


class RecordingScanner(NmapScanner):
    def __init__(self, responses: list[str]) -> None:
        self.nmap_path = "/usr/local/bin/nmap"
        self.responses = responses
        self.commands: list[list[str]] = []

    def _run(self, command: list[str], command_timeout_seconds: int) -> str:
        assert command_timeout_seconds == 120
        self.commands.append(command)
        return self.responses.pop(0)


def test_service_scan_targets_only_discovered_assets() -> None:
    xml = Path("tests/fixtures/nmap_sample.xml").read_text()
    scanner = RecordingScanner([xml, xml])
    progress: list[str] = []

    assets = scanner.discover(NmapScanConfig("192.168.1.0/24"), progress.append)

    assert len(assets) == 1
    assert len(scanner.commands) == 2
    assert "192.168.1.0/24" in scanner.commands[0]
    assert "192.168.1.0/24" not in scanner.commands[1]
    assert "192.168.1.25" in scanner.commands[1]
    assert any("Found 1 active device" in message for message in progress)


def test_preview_describes_fast_bounded_scan() -> None:
    scanner = RecordingScanner([])

    preview = scanner.preview(NmapScanConfig("192.168.1.0/24"))

    assert preview["service_scope"] == "discovered assets only"
    assert "-n" in preview["discovery_command"]
    assert "-T4" in preview["discovery_command"]
    assert "10s" in preview["discovery_command"]
