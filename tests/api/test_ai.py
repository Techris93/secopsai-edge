import json

import pytest

from secopsai_api.ai import AiReportProvider, redact_evidence
from secopsai_api.config import Settings


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


def test_openai_provider_uses_structured_outputs_and_preserves_findings(monkeypatch) -> None:
    response_report = {
        "title": "Weekly security report",
        "summary": "Three baseline devices require ownership validation.",
        "risk_level": "medium",
        "recommended_actions": ["Validate device ownership."],
        "technical_notes": ["No evidence of compromise was observed."],
    }
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps(response_report)}
                        ],
                    }
                ]
            }

    def fake_post(url: str, **kwargs: object) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("secopsai_api.ai.httpx.post", fake_post)
    settings = Settings(
        ai_provider="openai",
        ai_api_key="test-key",
        ai_model="gpt-5.4-mini",
    )
    findings = [{"type": "new_device", "severity": "medium"}]

    report = AiReportProvider(settings).generate({"findings": findings})

    request_body = captured["json"]
    assert isinstance(request_body, dict)
    assert request_body["store"] is False
    assert request_body["text"]["format"]["type"] == "json_schema"
    assert report["provider"] == "openai"
    assert report["model"] == "gpt-5.4-mini"
    assert report["findings"] == findings


def test_openai_provider_requires_server_side_api_key() -> None:
    settings = Settings(ai_provider="openai", ai_api_key=None)

    with pytest.raises(RuntimeError, match="AI_API_KEY"):
        AiReportProvider(settings).generate({"findings": []})
