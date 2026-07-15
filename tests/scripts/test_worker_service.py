from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
EDGE = ROOT / "scripts" / "edge"


def _macos_protected_root() -> bool:
    if sys.platform != "darwin":
        return False
    root = f"{ROOT.resolve()}/"
    home = f"{Path.home().resolve()}/"
    return any(
        root.startswith(home + prefix)
        for prefix in ("Documents/", "Desktop/", "Downloads/", "Library/Mobile Documents/")
    )


@pytest.mark.skipif(
    not _macos_protected_root(),
    reason="the protected source-tree guard is specific to macOS checkouts in privacy-protected folders",
)
def test_worker_service_rejects_protected_source_checkout() -> None:
    result = subprocess.run(
        [str(EDGE), "worker", "install-service", "--cloud"],
        cwd=ROOT,
        env={
            **os.environ,
            "SECOPSAI_EDGE_ALLOW_PROTECTED_SERVICE_ROOT": "no",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "privacy-protected folder" in result.stderr
    assert "released sensor" in result.stderr
