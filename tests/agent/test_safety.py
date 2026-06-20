import pytest

from secopsai_agent.safety import ScanSafetyError, validate_target_cidr


def test_private_cidr_is_allowed() -> None:
    assert validate_target_cidr("192.168.1.0/24") == "192.168.1.0/24"


def test_public_cidr_is_rejected() -> None:
    with pytest.raises(ScanSafetyError):
        validate_target_cidr("8.8.8.0/24")


def test_overly_broad_cidr_is_rejected() -> None:
    with pytest.raises(ScanSafetyError):
        validate_target_cidr("10.0.0.0/8")
