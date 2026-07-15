from __future__ import annotations

import hashlib
import hmac
from datetime import timedelta
from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.config import Settings
from secopsai_api.database import get_db
from secopsai_api.main import app
from secopsai_api.models import Base, NotificationDelivery, NotificationEndpoint, Sensor, Site, utcnow
from secopsai_api.notifications import _send_webhook, notify_event, process_due_deliveries
from secopsai_api.security import hash_secret


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def settings(**overrides: object) -> Settings:
    values = {
        "database_url": "sqlite+pysqlite://",
        "webhook_signing_secret": "test-signing-secret",
        "notification_max_attempts": 2,
    }
    values.update(overrides)
    return Settings(**values)


def test_webhook_uses_replay_resistant_hmac_headers(monkeypatch) -> None:
    response = Mock(status_code=202)
    post = Mock(return_value=response)
    monkeypatch.setattr("secopsai_api.notifications.httpx.post", post)
    monkeypatch.setattr("secopsai_api.notifications.time.time", lambda: 1_700_000_000)

    ok, detail = _send_webhook(
        "https://example.test/hook",
        "high_finding",
        {"title": "Risk"},
        "delivery-123",
        settings(),
    )

    assert ok is True
    assert detail == "Webhook delivered"
    body = post.call_args.kwargs["content"]
    headers = post.call_args.kwargs["headers"]
    expected = hmac.new(
        b"test-signing-secret",
        b"1700000000." + body,
        hashlib.sha256,
    ).hexdigest()
    assert headers["X-SecOpsAI-Delivery"] == "delivery-123"
    assert headers["X-SecOpsAI-Signature"] == f"sha256={expected}"


def test_failed_delivery_is_persisted_retried_and_exhausted(monkeypatch) -> None:
    db = make_session()
    site = Site(name="Pilot")
    endpoint = NotificationEndpoint(
        site_id=None,
        name="Webhook",
        type="webhook",
        target="https://example.test/hook",
        enabled=True,
        events=["high_finding"],
    )
    db.add_all([site, endpoint])
    db.commit()
    monkeypatch.setattr(
        "secopsai_api.notifications.deliver_notification",
        lambda *args, **kwargs: (False, "temporary outage"),
    )

    deliveries = notify_event(
        db,
        "high_finding",
        {"title": "Risk"},
        site_id=site.id,
        settings=settings(),
    )
    delivery = deliveries[0]
    assert delivery.status == "retrying"
    assert delivery.attempts == 1
    assert endpoint.last_error == "temporary outage"

    delivery.next_attempt_at = utcnow() - timedelta(seconds=1)
    result = process_due_deliveries(db, settings=settings())

    assert result == {"processed": 1, "delivered": 0, "retrying": 0, "failed": 1}
    persisted = db.scalar(select(NotificationDelivery).where(NotificationDelivery.id == delivery.id))
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.attempts == 2


def test_site_scoped_endpoint_does_not_receive_another_sites_event(monkeypatch) -> None:
    db = make_session()
    site_a = Site(name="A")
    site_b = Site(name="B")
    db.add_all([site_a, site_b])
    db.flush()
    endpoint = NotificationEndpoint(
        site_id=site_a.id,
        name="Site A webhook",
        type="webhook",
        target="https://example.test/hook",
        enabled=True,
        events=[],
    )
    db.add(endpoint)
    db.commit()
    monkeypatch.setattr(
        "secopsai_api.notifications.deliver_notification",
        lambda *args, **kwargs: (True, "delivered"),
    )

    deliveries = notify_event(db, "scan_completed", {}, site_id=site_b.id, settings=settings())

    assert deliveries == []
    assert db.scalar(select(NotificationDelivery)) is None


def test_delivery_history_and_manual_retry_api(monkeypatch) -> None:
    db = make_session()
    endpoint = NotificationEndpoint(
        name="Webhook",
        type="webhook",
        target="https://example.test/hook",
        enabled=True,
        events=[],
    )
    db.add(endpoint)
    db.flush()
    delivery = NotificationDelivery(
        endpoint_id=endpoint.id,
        event_type="high_finding",
        payload={"title": "Risk"},
        status="failed",
        attempts=4,
        max_attempts=4,
        next_attempt_at=utcnow(),
        response_detail="outage",
    )
    db.add(delivery)
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        "secopsai_api.notifications.deliver_notification",
        lambda *args, **kwargs: (True, "delivered"),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer dev-admin-token"}

    history = client.get("/api/v1/notification-deliveries", headers=headers)
    assert history.status_code == 200
    assert history.json()[0]["status"] == "failed"
    assert "payload" not in history.json()[0]

    retried = client.post(
        f"/api/v1/notification-deliveries/{delivery.id}/retry",
        headers=headers,
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "delivered"
    assert retried.json()["attempts"] == 1


def test_notification_scheduler_alerts_once_for_stale_sensor_and_rearms_on_heartbeat(monkeypatch) -> None:
    db = make_session()
    site = Site(name="Pilot")
    sensor = Sensor(
        site=site,
        name="MacBook Sensor",
        hostname="macbook",
        token_hash=hash_secret("sensor-token"),
        status="online",
        last_seen_at=utcnow() - timedelta(minutes=10),
    )
    endpoint = NotificationEndpoint(
        site_id=site.id,
        name="Offline webhook",
        type="webhook",
        target="https://example.test/hook",
        enabled=True,
        events=["sensor_offline"],
    )
    db.add_all([site, sensor, endpoint])
    db.commit()

    monkeypatch.setattr(
        "secopsai_api.notifications.deliver_notification",
        lambda *args, **kwargs: (True, "delivered"),
    )
    app.dependency_overrides[get_db] = lambda: (yield db)
    client = TestClient(app)
    headers = {"Authorization": "Bearer dev-admin-token"}

    first = client.post("/api/v1/notification-deliveries/run-due", headers=headers)

    assert first.status_code == 200
    assert first.json()["sensor_offline_alerts"] == 1
    assert sensor.status == "offline"
    assert sensor.offline_alerted_at is not None
    assert db.scalar(select(NotificationDelivery).where(NotificationDelivery.event_type == "sensor_offline")) is not None

    second = client.post("/api/v1/notification-deliveries/run-due", headers=headers)

    assert second.status_code == 200
    assert second.json()["sensor_offline_alerts"] == 0
    assert len(db.scalars(select(NotificationDelivery).where(NotificationDelivery.event_type == "sensor_offline")).all()) == 1

    heartbeat = client.post(
        f"/api/v1/sensors/{sensor.id}/heartbeat",
        headers={"X-Sensor-Token": "sensor-token"},
        json={"status": "online", "details": {"state": "waiting"}},
    )

    assert heartbeat.status_code == 200
    assert sensor.offline_alerted_at is None

    sensor.last_seen_at = utcnow() - timedelta(minutes=10)
    db.commit()
    third = client.post("/api/v1/notification-deliveries/run-due", headers=headers)

    assert third.status_code == 200
    assert third.json()["sensor_offline_alerts"] == 1
    assert len(db.scalars(select(NotificationDelivery).where(NotificationDelivery.event_type == "sensor_offline")).all()) == 2


def test_notification_scheduler_does_not_alert_never_seen_sensor(monkeypatch) -> None:
    db = make_session()
    site = Site(name="Pilot")
    sensor = Sensor(
        site=site,
        name="New Sensor",
        token_hash=hash_secret("sensor-token"),
        status="registered",
        last_seen_at=None,
    )
    endpoint = NotificationEndpoint(
        site_id=site.id,
        name="Offline webhook",
        type="webhook",
        target="https://example.test/hook",
        enabled=True,
        events=["sensor_offline"],
    )
    db.add_all([site, sensor, endpoint])
    db.commit()
    monkeypatch.setattr(
        "secopsai_api.notifications.deliver_notification",
        lambda *args, **kwargs: (True, "delivered"),
    )
    app.dependency_overrides[get_db] = lambda: (yield db)
    response = TestClient(app).post(
        "/api/v1/notification-deliveries/run-due",
        headers={"Authorization": "Bearer dev-admin-token"},
    )

    assert response.status_code == 200
    assert response.json()["sensor_offline_alerts"] == 0
    assert db.scalar(select(NotificationDelivery).where(NotificationDelivery.event_type == "sensor_offline")) is None
