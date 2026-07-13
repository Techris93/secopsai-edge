from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "scripts" / "bootstrap-secopsai-edge.sh"
BUILD_RELEASE = ROOT / "scripts" / "build-release"


def _write_release(
    fixture_dir: Path,
    *,
    marker: str,
    fail_install: bool = False,
    unsafe_member: bool = False,
) -> None:
    archive_name = "secopsai-edge-0.3.1.tar.gz"
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
            info = tarfile.TarInfo("secopsai-edge-0.3.1/scripts/install-secopsai-edge.sh")
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


def _fake_gh(bin_dir: Path) -> None:
    gh = bin_dir / "gh"
    gh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "auth" ] && [ "${2:-}" = "status" ]; then
  exit 0
fi
if [ "${1:-}" != "release" ] || [ "${2:-}" != "download" ]; then
  exit 64
fi
shift 2
destination=""
patterns=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dir) shift; destination="$1" ;;
    --pattern) shift; patterns+=("$1") ;;
  esac
  shift
done
[ -n "$destination" ]
mkdir -p "$destination"
for pattern in "${patterns[@]}"; do
  cp "$RELEASE_FIXTURES/$pattern" "$destination/$pattern"
done
printf '%s\n' "${patterns[@]}" > "$GH_DOWNLOAD_LOG"
""",
        encoding="utf-8",
    )
    gh.chmod(0o755)


def _run_bootstrap(
    tmp_path: Path,
    *extra: str,
    download_method: str = "curl",
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _fake_curl(bin_dir)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["RELEASE_FIXTURES"] = str(tmp_path / "fixtures")
    env["SECOPSAI_EDGE_DOWNLOAD_METHOD"] = download_method
    return subprocess.run(
        [
            "bash",
            str(BOOTSTRAP),
            "--version",
            "0.3.1",
            "--install-dir",
            str(tmp_path / "install"),
            *extra,
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_bootstrap_downloads_private_release_with_authenticated_gh(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    _write_release(fixtures, marker="private-release")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _fake_gh(bin_dir)
    log = tmp_path / "gh-download.log"

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["RELEASE_FIXTURES"] = str(fixtures)
    env["GH_DOWNLOAD_LOG"] = str(log)
    env["SECOPSAI_EDGE_DOWNLOAD_METHOD"] = "auto"
    result = subprocess.run(
        [
            "bash",
            str(BOOTSTRAP),
            "--version",
            "0.3.1",
            "--install-dir",
            str(tmp_path / "install"),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "install" / "installed-version.txt").read_text().strip() == "private-release"
    assert log.read_text().splitlines() == [
        "secopsai-edge-0.3.1.tar.gz",
        "secopsai-edge-0.3.1.tar.gz.sha256",
    ]


def test_release_archive_version_comes_from_committed_head(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "api" / "secopsai_api").mkdir(parents=True)
    (repo / "agent" / "secopsai_agent").mkdir(parents=True)
    (repo / "web").mkdir()
    (repo / "scripts" / "build-release").write_bytes(BUILD_RELEASE.read_bytes())
    (repo / "scripts" / "build-release").chmod(0o755)
    (repo / "scripts" / "bootstrap-secopsai-edge.sh").write_bytes(BOOTSTRAP.read_bytes())
    (repo / "scripts" / "bootstrap-secopsai-edge.sh").chmod(0o755)
    (repo / "api" / "secopsai_api" / "__init__.py").write_text('__version__ = "0.2.1"\n')
    (repo / "agent" / "secopsai_agent" / "__init__.py").write_text('__version__ = "0.2.1"\n')
    (repo / "web" / "package.json").write_text('{"version":"0.2.1"}\n')
    (repo / "committed.txt").write_text("committed\n")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.test", "commit", "-qm", "fixture"],
        cwd=repo,
        check=True,
    )

    for path in (
        repo / "api" / "secopsai_api" / "__init__.py",
        repo / "agent" / "secopsai_agent" / "__init__.py",
    ):
        path.write_text('__version__ = "0.2.2"\n')
    (repo / "web" / "package.json").write_text('{"version":"0.2.2"}\n')

    mismatch = subprocess.run(
        [str(repo / "scripts" / "build-release"), "0.2.2", str(tmp_path / "bad-dist")],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    assert mismatch.returncode != 0
    assert "does not match component version 0.2.1" in mismatch.stderr

    committed = subprocess.run(
        [str(repo / "scripts" / "build-release"), "0.2.1", str(tmp_path / "good-dist")],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    assert committed.returncode == 0, committed.stderr
    archive = tmp_path / "good-dist" / "secopsai-edge-0.2.1.tar.gz"
    with tarfile.open(archive, "r:gz") as bundle:
        api_member = bundle.extractfile("secopsai-edge-0.2.1/api/secopsai_api/__init__.py")
        assert api_member is not None
        assert api_member.read() == b'__version__ = "0.2.1"\n'


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
