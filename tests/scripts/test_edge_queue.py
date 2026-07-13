from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EDGE = ROOT / "scripts" / "edge"


def test_queue_command_posts_normalized_job_without_scanning(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    args_file = tmp_path / "curl-args.txt"
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$@\" > '{args_file}'\n"
        "printf '%s' '{\"id\":\"job-1\",\"status\":\"queued\"}'\n",
        encoding="utf-8",
    )
    fake_curl.chmod(0o700)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "SECOPSAI_EDGE_CLOUD_ENV_FILE": str(tmp_path / "cloud.env"),
            "SECOPSAI_EDGE_CLOUD_SENSOR_ENV_FILE": str(tmp_path / "cloud-sensor.env"),
            "SECOPSAI_CLOUD_API_URL": "https://edge.example.test",
            "SECOPSAI_CLOUD_ADMIN_TOKEN": "test-admin-token",
            "SECOPSAI_CLOUD_SENSOR_ID": "sensor-1",
        }
    )

    result = subprocess.run(
        [str(EDGE), "queue", "192.168.1.7/24", "--cloud", "--wifi"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"id": "job-1", "status": "queued"}
    args = args_file.read_text(encoding="utf-8").splitlines()
    assert "https://edge.example.test/api/v1/scan-jobs" in args
    assert "Authorization: Bearer test-admin-token" in args
    body = args[args.index("--data") + 1]
    assert json.loads(body) == {
        "target_cidr": "192.168.1.0/24",
        "include_wifi": True,
        "sensor_id": "sensor-1",
    }


def test_queue_command_rejects_public_or_broad_targets_before_http(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "SECOPSAI_EDGE_CLOUD_ENV_FILE": str(tmp_path / "cloud.env"),
            "SECOPSAI_EDGE_CLOUD_SENSOR_ENV_FILE": str(tmp_path / "cloud-sensor.env"),
            "SECOPSAI_CLOUD_API_URL": "https://edge.example.test",
            "SECOPSAI_CLOUD_ADMIN_TOKEN": "test-admin-token",
        }
    )

    result = subprocess.run(
        [str(EDGE), "queue", "8.8.8.0/24", "--cloud"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "RFC1918" in result.stderr
