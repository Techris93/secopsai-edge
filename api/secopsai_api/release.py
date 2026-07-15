from __future__ import annotations

from typing import Literal

from packaging.version import InvalidVersion, Version

ReleaseStatus = Literal["current", "outdated", "ahead", "unknown", "disabled"]


def sensor_release_status(
    sensor_version: str | None,
    recommended_version: str | None,
    *,
    disabled: bool = False,
) -> tuple[ReleaseStatus, bool | None]:
    """Return a safe operator-facing comparison without trusting arbitrary versions."""
    if disabled:
        return "disabled", False
    if not sensor_version or not recommended_version:
        return "unknown", None
    try:
        installed = Version(sensor_version.lstrip("v"))
        recommended = Version(recommended_version.lstrip("v"))
    except InvalidVersion:
        return "unknown", None
    if installed == recommended:
        return "current", False
    if installed < recommended:
        return "outdated", True
    return "ahead", False
