from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess


ROOT = Path(__file__).resolve().parents[2]
EDGE = ROOT / "scripts" / "edge"


def _fake_curl(bin_dir: Path, args_file: Path) -> None:
    curl = bin_dir / "curl"
    curl.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$@\" > '{args_file}'\n"
        "url=''\n"
        "for arg in \"$@\"; do case \"$arg\" in *'/rotate-token') url=\"$arg\";; esac; done\n"
        "sensor_id=\"${url##*/sensors/}\"\n"
        "sensor_id=\"${sensor_id%/rotate-token}\"\n"
        "printf '%s' \"{\\\"sensor_id\\\":\\\"$sensor_id\\\",\\\"sensor_token\\\":\\\"replacement-secret\\\"}\"\n",
        encoding="utf-8",
    )
    curl.chmod(0o700)


def test_cloud_sensor_rotation_replaces_credentials_atomically(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    args_file = tmp_path / "curl-args.txt"
    _fake_curl(bin_dir, args_file)
    sensor_file = tmp_path / "cloud-sensor.env"
    sensor_file.write_text(
        "SECOPSAI_CLOUD_SENSOR_ID=sensor-old\nSECOPSAI_CLOUD_SENSOR_TOKEN=old-secret\n",
        encoding="utf-8",
    )
    sensor_file.chmod(0o600)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "SECOPSAI_EDGE_CLOUD_ENV_FILE": str(tmp_path / "cloud.env"),
            "SECOPSAI_EDGE_CLOUD_SENSOR_ENV_FILE": str(sensor_file),
            "SECOPSAI_CLOUD_API_URL": "https://edge.example.test",
            "SECOPSAI_CLOUD_SENSOR_ID": "sensor-old",
            "SECOPSAI_CLOUD_ADMIN_TOKEN": "test-admin-token",
        }
    )

    result = subprocess.run(
        [str(EDGE), "cloud", "rotate-sensor-token"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "sensor-old" in result.stdout
    assert "replacement-secret" not in result.stdout
    assert "./scripts/edge worker restart" in result.stdout
    assert sensor_file.read_text(encoding="utf-8") == (
        "SECOPSAI_CLOUD_SENSOR_ID=sensor-old\n"
        "SECOPSAI_CLOUD_SENSOR_TOKEN=replacement-secret\n"
    )
    assert stat.S_IMODE(sensor_file.stat().st_mode) == 0o600

    args = args_file.read_text(encoding="utf-8").splitlines()
    assert "https://edge.example.test/api/v1/sensors/sensor-old/rotate-token" in args
    assert "Authorization: Bearer test-admin-token" in args


def test_cloud_reauth_alias_accepts_explicit_sensor_id(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _fake_curl(bin_dir, tmp_path / "curl-args.txt")
    sensor_file = tmp_path / "cloud-sensor.env"

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "SECOPSAI_EDGE_CLOUD_ENV_FILE": str(tmp_path / "cloud.env"),
            "SECOPSAI_EDGE_CLOUD_SENSOR_ENV_FILE": str(sensor_file),
            "SECOPSAI_CLOUD_API_URL": "https://edge.example.test",
            "SECOPSAI_CLOUD_ADMIN_TOKEN": "test-admin-token",
        }
    )

    result = subprocess.run(
        [str(EDGE), "cloud", "reauth", "sensor-explicit"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "SECOPSAI_CLOUD_SENSOR_ID=sensor-explicit" in sensor_file.read_text(encoding="utf-8")
    args = (tmp_path / "curl-args.txt").read_text(encoding="utf-8").splitlines()
    assert "https://edge.example.test/api/v1/sensors/sensor-explicit/rotate-token" in args
