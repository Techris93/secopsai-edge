from __future__ import annotations

from secopsai_agent import cli


class FakeClient:
    def __init__(self) -> None:
        self.heartbeats: list[tuple[str, str, dict[str, object]]] = []
        self.claims = 0

    def heartbeat(self, sensor_id: str, status: str = "online", details: dict[str, object] | None = None) -> dict[str, str]:
        self.heartbeats.append((sensor_id, status, details or {}))
        return {"status": "ok"}

    def claim_scan_job(self, sensor_id: str) -> None:
        self.claims += 1
        return None


def test_worker_sends_heartbeat_before_single_idle_poll(monkeypatch) -> None:
    fake_client = FakeClient()
    monkeypatch.setattr(cli, "SecOpsApiClient", lambda *args, **kwargs: fake_client)

    result = cli._run_worker(
        scanner=object(),
        api_url="https://api.example.test",
        sensor_id="sensor-1",
        sensor_token="token",
        poll_interval=30,
        once=True,
    )

    assert result == 0
    assert fake_client.claims == 1
    assert len(fake_client.heartbeats) == 1
    sensor_id, status, details = fake_client.heartbeats[0]
    assert (sensor_id, status) == ("sensor-1", "online")
    assert details["mode"] == "worker"
    assert details["state"] == "waiting"
    assert details["version"] == "0.2.4"
    assert details["os"]
    assert details["hostname"]


def test_scanning_heartbeat_includes_job_and_stops() -> None:
    fake_client = FakeClient()
    stop = __import__("threading").Event()

    class StopAfterFirst:
        def heartbeat(self, sensor_id, status="online", details=None):
            result = fake_client.heartbeat(sensor_id, status, details)
            stop.set()
            return result

    cli._heartbeat_loop(StopAfterFirst(), "sensor-1", stop, "job-1", interval=1)

    assert fake_client.heartbeats[0][2]["state"] == "scanning"
    assert fake_client.heartbeats[0][2]["job_id"] == "job-1"
