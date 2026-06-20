from secopsai_api.ai import redact_evidence


def test_redact_evidence_removes_sensitive_identifiers() -> None:
    evidence = {
        "ip": "192.168.1.20",
        "mac": "aa:bb:cc:dd:ee:ff",
        "hostname": "finance-macbook",
        "port": 22,
    }

    redacted = redact_evidence(evidence)

    assert redacted["ip"] == "192.168.1.20"
    assert redacted["port"] == 22
    assert redacted["mac"] == "[redacted]"
    assert redacted["hostname"] == "[redacted]"
