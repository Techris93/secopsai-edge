from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "scripts" / "bootstrap-secopsai-edge.sh"


def _write_release(
    fixture_dir: Path,
    *,
    marker: str,
    fail_install: bool = False,
    unsafe_member: bool = False,
) -> None:
    archive_name = "secopsai-edge-0.2.0.tar.gz"
    archive = fixture_dir / archive_name
    installer = f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' \"$@\" > \"$(dirname \"$0\")/../install-args.txt\"
printf '%s\\n' {marker!r} > \"$(dirname \"$0\")/../installed-version.txt\"
{'exit 42' if fail_install else ''}
""".encode()

    with tarfile.open(archive, "w:gz") as bundle:
        if unsafe_member:
            info = tarfile.TarInfo("../outside.txt")
            payload = b"must not escape"
        else:
            info = tarfile.TarInfo("secopsai-edge-0.2.0/scripts/install-secopsai-edge.sh")
            info.mode = 0o755
            payload = installer
        info.size = len(payload)
        bundle.addfile(info, io.BytesIO(payload))

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (fixture_dir / f"{archive_name}.sha256").write_text(
        f"{digest}  {archive_name}\n",
        encoding="ascii",
    )


def _fake_curl(bin_dir: Path) -> None:
    curl = bin_dir / "curl"
    curl.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
output=""
url=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    -o) shift; output="$1" ;;
    http*) url="$1" ;;
  esac
  shift
done
cp "$RELEASE_FIXTURES/${url##*/}" "$output"
""",
        encoding="utf-8",
    )
    curl.chmod(0o755)


def _run_bootstrap(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _fake_curl(bin_dir)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["RELEASE_FIXTURES"] = str(tmp_path / "fixtures")
    return subprocess.run(
        [
            "bash",
            str(BOOTSTRAP),
            "--version",
            "0.2.0",
            "--install-dir",
            str(tmp_path / "install"),
            *extra,
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_bootstrap_installs_upgrades_and_rolls_back(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()

    _write_release(fixtures, marker="v1")
    first = _run_bootstrap(tmp_path, "--cloud", "--api-url", "https://api.example.test")
    assert first.returncode == 0, first.stderr
    install = tmp_path / "install"
    assert (install / "installed-version.txt").read_text().strip() == "v1"
    assert (install / "install-args.txt").read_text().splitlines() == [
        "--cloud",
        "--api-url",
        "https://api.example.test",
    ]

    credential = install / ".cloud-sensor.env"
    credential.write_text("SECOPSAI_SENSOR_TOKEN=preserved\n", encoding="utf-8")
    credential.chmod(0o600)
    _write_release(fixtures, marker="v2")
    upgraded = _run_bootstrap(tmp_path, "--upgrade")
    assert upgraded.returncode == 0, upgraded.stderr
    assert (install / "installed-version.txt").read_text().strip() == "v2"
    assert credential.read_text() == "SECOPSAI_SENSOR_TOKEN=preserved\n"
    assert (tmp_path / "install.previous" / "installed-version.txt").read_text().strip() == "v1"

    _write_release(fixtures, marker="broken", fail_install=True)
    failed = _run_bootstrap(tmp_path, "--upgrade")
    assert failed.returncode == 42
    assert (install / "installed-version.txt").read_text().strip() == "v2"
    assert credential.read_text() == "SECOPSAI_SENSOR_TOKEN=preserved\n"


def test_bootstrap_rejects_unsafe_archive_paths(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    _write_release(fixtures, marker="unsafe", unsafe_member=True)

    result = _run_bootstrap(tmp_path)

    assert result.returncode != 0
    assert "unsafe path in release archive" in result.stderr
    assert not (tmp_path / "outside.txt").exists()
    assert not (tmp_path / "install").exists()
