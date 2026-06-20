from secopsai_api.security import create_dashboard_session, verify_dashboard_session


def test_dashboard_session_round_trip() -> None:
    token = create_dashboard_session()

    assert verify_dashboard_session(token)


def test_dashboard_session_rejects_tampering() -> None:
    token = create_dashboard_session()
    prefix, payload, signature = token.split(".")
    replacement = "A" if not signature.endswith("A") else "B"
    tampered = f"{prefix}.{payload}.{signature[:-1]}{replacement}"

    assert not verify_dashboard_session(tampered)
