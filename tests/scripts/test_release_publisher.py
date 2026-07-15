from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH = ROOT / "scripts" / "release-publish"


FAKE_GH = """#!/usr/bin/env bash
set -euo pipefail

log_file="$GH_LOG"
printf '%s\\n' "$*" >> "$log_file"
scenario="${GH_SCENARIO:-create}"
if [ "${1:-}" != "release" ]; then exit 64; fi
case "${2:-}" in
  view)
    if [ "$scenario" = "existing" ]; then exit 0; fi
    if [ "$scenario" = "race" ]; then
      count="$(grep -c '^release view' "$log_file" || true)"
      [ "$count" -ge 2 ] && exit 0
    fi
    exit 1
    ;;
  create)
    [ "$scenario" = "create" ] && exit 0
    exit 1
    ;;
  upload)
    [ "$scenario" = "existing" ] || [ "$scenario" = "race" ]
    ;;
  *) exit 64 ;;
esac
"""


def _run(tmp_path: Path, scenario: str) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(FAKE_GH, encoding="utf-8")
    fake_gh.chmod(0o755)
    asset = tmp_path / "package.tar.gz"
    asset.write_bytes(b"package")
    log = tmp_path / "gh.log"
    env = os.environ.copy()
    env.update({"PATH": f"{bin_dir}:{env['PATH']}", "GH_LOG": str(log), "GH_SCENARIO": scenario})
    return subprocess.run(
        [str(PUBLISH), "v9.9.9", str(asset)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_existing_release_refreshes_assets(tmp_path: Path) -> None:
    result = _run(tmp_path, "existing")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "gh.log").read_text().splitlines() == [
        "release view v9.9.9 --json tagName",
        "release upload v9.9.9 --clobber " + str(tmp_path / "package.tar.gz"),
    ]


def test_new_release_is_created(tmp_path: Path) -> None:
    result = _run(tmp_path, "create")

    assert result.returncode == 0, result.stderr
    lines = (tmp_path / "gh.log").read_text().splitlines()
    assert lines[0] == "release view v9.9.9 --json tagName"
    assert lines[1].startswith("release create v9.9.9 --verify-tag --generate-notes")


def test_duplicate_create_race_refreshes_release(tmp_path: Path) -> None:
    result = _run(tmp_path, "race")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "gh.log").read_text().splitlines() == [
        "release view v9.9.9 --json tagName",
        "release create v9.9.9 --verify-tag --generate-notes " + str(tmp_path / "package.tar.gz"),
        "release view v9.9.9 --json tagName",
        "release upload v9.9.9 --clobber " + str(tmp_path / "package.tar.gz"),
    ]


def test_missing_release_is_reported_after_create_failure(tmp_path: Path) -> None:
    result = _run(tmp_path, "missing")

    assert result.returncode == 1
    assert "unable to create or find release v9.9.9" in result.stderr
