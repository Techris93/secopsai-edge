from __future__ import annotations

import hashlib
import hmac
import json
import smtplib
import time
from datetime import timedelta
from email.message import EmailMessage
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from secopsai_api.config import Settings, get_settings
from secopsai_api.models import NotificationDelivery, NotificationEndpoint, Site, utcnow


RETRYABLE_STATUSES = {"queued", "retrying"}


def notify_event(
    db: Session,
    event_type: str,
    payload: dict[str, Any],
    *,
    site_id: str | None = None,
    settings: Settings | None = None,
) -> list[NotificationDelivery]:
    """Persist matching deliveries and make one immediate, recorded attempt."""
    settings = settings or get_settings()
    organization_id = None
    if site_id:
        site = db.get(Site, site_id)
        organization_id = site.organization_id if site else None
    query = select(NotificationEndpoint).where(NotificationEndpoint.enabled.is_(True))
    if organization_id:
        query = query.where(NotificationEndpoint.organization_id == organization_id)
    deliveries: list[NotificationDelivery] = []
    for endpoint in db.scalars(query).all():
        if endpoint.site_id and endpoint.site_id != site_id:
            continue
        if endpoint.events and event_type not in endpoint.events:
            continue
        delivery = NotificationDelivery(
            organization_id=endpoint.organization_id,
            endpoint_id=endpoint.id,
            site_id=site_id,
            event_type=event_type,
            payload=payload,
            max_attempts=max(1, settings.notification_max_attempts),
            next_attempt_at=utcnow(),
        )
        db.add(delivery)
        db.flush()
        attempt_delivery(db, delivery, endpoint=endpoint, settings=settings)
        deliveries.append(delivery)
    return deliveries


def test_notification(
    db: Session,
    endpoint: NotificationEndpoint,
    settings: Settings | None = None,
) -> NotificationDelivery:
    settings = settings or get_settings()
    delivery = NotificationDelivery(
        organization_id=endpoint.organization_id,
        endpoint_id=endpoint.id,
        site_id=endpoint.site_id,
        event_type="test",
        payload={
            "title": "SecOpsAI Edge notification test",
            "summary": "This verifies that this notification endpoint can receive SecOpsAI events.",
        },
        max_attempts=max(1, settings.notification_max_attempts),
        next_attempt_at=utcnow(),
    )
    db.add(delivery)
    db.flush()
    attempt_delivery(db, delivery, endpoint=endpoint, settings=settings)
    return delivery


def process_due_deliveries(
    db: Session,
    *,
    settings: Settings | None = None,
    limit: int | None = None,
    organization_id: str | None = None,
) -> dict[str, int]:
    settings = settings or get_settings()
    batch_size = max(1, min(limit or settings.notification_batch_size, 250))
    query = (
        select(NotificationDelivery)
        .where(
            NotificationDelivery.status.in_(RETRYABLE_STATUSES),
            NotificationDelivery.next_attempt_at <= utcnow(),
        )
        .order_by(NotificationDelivery.next_attempt_at, NotificationDelivery.created_at)
        .limit(batch_size)
    )
    if organization_id:
        query = query.where(NotificationDelivery.organization_id == organization_id)
    totals = {"processed": 0, "delivered": 0, "retrying": 0, "failed": 0}
    for delivery in db.scalars(query).all():
        endpoint = db.get(NotificationEndpoint, delivery.endpoint_id)
        if endpoint is None or not endpoint.enabled:
            delivery.status = "failed"
            delivery.response_detail = "Notification endpoint is unavailable or disabled"
            delivery.updated_at = utcnow()
        else:
            attempt_delivery(db, delivery, endpoint=endpoint, settings=settings)
        totals["processed"] += 1
        totals[delivery.status] += 1
    db.flush()
    return totals


def attempt_delivery(
    db: Session,
    delivery: NotificationDelivery,
    *,
    endpoint: NotificationEndpoint,
    settings: Settings,
) -> None:
    if delivery.status not in RETRYABLE_STATUSES:
        return
    now = utcnow()
    delivery.attempts += 1
    delivery.last_attempt_at = now
    ok, detail = deliver_notification(
        endpoint,
        delivery.event_type,
        delivery.payload,
        delivery_id=delivery.id,
        settings=settings,
    )
    delivery.response_detail = detail[:2000]
    delivery.updated_at = now
    if ok:
        delivery.status = "delivered"
        delivery.delivered_at = now
        endpoint.last_sent_at = now
        endpoint.last_error = None
    elif delivery.attempts >= delivery.max_attempts:
        delivery.status = "failed"
        endpoint.last_error = detail[:2000]
    else:
        delivery.status = "retrying"
        delay_seconds = min(60 * (5 ** (delivery.attempts - 1)), 3600)
        delivery.next_attempt_at = now + timedelta(seconds=delay_seconds)
        endpoint.last_error = detail[:2000]
    endpoint.updated_at = now
    db.flush()


def deliver_notification(
    endpoint: NotificationEndpoint,
    event_type: str,
    payload: dict[str, Any],
    *,
    delivery_id: str,
    settings: Settings,
) -> tuple[bool, str]:
    try:
        if endpoint.type == "webhook":
            return _send_webhook(endpoint.target, event_type, payload, delivery_id, settings)
        if endpoint.type == "email":
            return _send_email(endpoint.target, event_type, payload, settings)
        if endpoint.type == "telegram":
            return _send_telegram(endpoint.target, event_type, payload, settings)
        return False, f"Unsupported notification type: {endpoint.type}"
    except Exception as exc:  # pragma: no cover - defensive boundary for external services
        return False, str(exc)


def _send_webhook(
    target: str,
    event_type: str,
    payload: dict[str, Any],
    delivery_id: str,
    settings: Settings,
) -> tuple[bool, str]:
    body = json.dumps(
        {"id": delivery_id, "event": event_type, "payload": payload},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    timestamp = str(int(time.time()))
    signed = timestamp.encode("ascii") + b"." + body
    signature = hmac.new(
        settings.webhook_signing_secret.encode("utf-8"), signed, hashlib.sha256
    ).hexdigest()
    response = httpx.post(
        target,
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-SecOpsAI-Delivery": delivery_id,
            "X-SecOpsAI-Event": event_type,
            "X-SecOpsAI-Timestamp": timestamp,
            "X-SecOpsAI-Signature": f"sha256={signature}",
        },
        timeout=15,
    )
    if response.status_code >= 400:
        return False, f"Webhook returned HTTP {response.status_code}"
    return True, "Webhook delivered"


def _send_email(target: str, event_type: str, payload: dict[str, Any], settings: Settings) -> tuple[bool, str]:
    if not settings.smtp_host:
        return False, "SMTP_HOST is not configured"
    message = EmailMessage()
    message["Subject"] = f"SecOpsAI Edge: {payload.get('title', event_type)}"
    message["From"] = settings.smtp_from
    message["To"] = target
    message.set_content(
        "\n".join(
            [
                f"Event: {event_type}",
                f"Summary: {payload.get('summary', '')}",
                "",
                "Evidence:",
                str(payload.get("evidence", payload)),
            ]
        )
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
    return True, "Email delivered"


def _send_telegram(target: str, event_type: str, payload: dict[str, Any], settings: Settings) -> tuple[bool, str]:
    if not settings.telegram_bot_token:
        return False, "TELEGRAM_BOT_TOKEN is not configured"
    text = f"SecOpsAI Edge: {payload.get('title', event_type)}\n{payload.get('summary', '')}"
    response = httpx.post(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
        json={"chat_id": target, "text": text},
        timeout=15,
    )
    if response.status_code >= 400:
        return False, f"Telegram returned HTTP {response.status_code}"
    return True, "Telegram delivered"
