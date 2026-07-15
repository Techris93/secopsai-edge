from secopsai_api.release import sensor_release_status


def test_release_status_compares_normalized_versions() -> None:
    assert sensor_release_status("v0.3.11", "0.3.11") == ("current", False)
    assert sensor_release_status("0.3.10", "v0.3.11") == ("outdated", True)
    assert sensor_release_status("0.4.0", "0.3.11") == ("ahead", False)


def test_release_status_does_not_trust_invalid_or_missing_versions() -> None:
    assert sensor_release_status(None, "0.3.11") == ("unknown", None)
    assert sensor_release_status("not-a-version", "0.3.11") == ("unknown", None)
    assert sensor_release_status("0.3.10", "not-a-version") == ("unknown", None)
    assert sensor_release_status("0.3.10", "0.3.11", disabled=True) == ("disabled", False)
