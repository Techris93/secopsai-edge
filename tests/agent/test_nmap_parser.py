from pathlib import Path

from secopsai_agent.nmap_parser import parse_nmap_xml


def test_parse_nmap_xml_extracts_asset_and_open_services() -> None:
    xml = Path("tests/fixtures/nmap_sample.xml").read_text()

    assets = parse_nmap_xml(xml)

    assert len(assets) == 1
    assert assets[0].ip == "192.168.1.25"
    assert assets[0].mac == "AA:BB:CC:DD:EE:FF"
    assert assets[0].vendor == "Apple"
    assert assets[0].hostname == "Chris-MacBook.local"
    assert len(assets[0].services) == 1
    assert assets[0].services[0].port == 22
