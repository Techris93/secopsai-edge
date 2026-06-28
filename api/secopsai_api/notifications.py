from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from secopsai_api.config import Settings, get_settings
from secopsai_api.models import NotificationEndpoint, utcnow


def notify_event(
    db: Session,
    event_type: str,
    payload: dict[str, Any],
    *,
    site_id: str | None = None,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    query = select(NotificationEndpoint).where(NotificationEndpoint.enabled.is_(True))
    endpoints = db.scalars(query).all()
    for endpoint in endpoints:
        if endpoint.site_id and site_id and endpoint.site_id != site_id:
            continue
        if endpoint.events and event_type not in endpoint.events:
            continue
        ok, detail = deliver_notification(endpoint, event_type, payload, settings=settings)
        endpoint.last_sent_at = utcnow() if ok else endpoint.last_sent_at
        endpoint.last_error = None if ok else detail
        endpoint.updated_at = utcnow()
    db.flush()


def test_notification(endpoint: NotificationEndpoint, settings: Settings | None = None) -> tuple[bool, str]:
    return deliver_notification(
        endpoint,
        "test",
        {
            "title": "SecOpsAI Edge notification test",
            "summary": "This verifies that this notification endpoint can receive SecOpsAI events.",
        },
        settings=settings or get_settings(),
    )


def deliver_notification(
    endpoint: NotificationEndpoint,
    event_type: str,
    payload: dict[str, Any],
    *,
    settings: Settings,
) -> tuple[bool, str]:
    try:
        if endpoint.type == "webhook":
            return _send_webhook(endpoint.target, event_type, payload)
        if endpoint.type == "email":
            return _send_email(endpoint.target, event_type, payload, settings)
        if endpoint.type == "telegram":
            return _send_telegram(endpoint.target, event_type, payload, settings)
        return False, f"Unsupported notification type: {endpoint.type}"
    except Exception as exc:  # pragma: no cover - defensive boundary for external services
        return False, str(exc)


def _send_webhook(target: str, event_type: str, payload: dict[str, Any]) -> tuple[bool, str]:
    response = httpx.post(
        target,
        json={"event": event_type, "payload": payload},
        headers={"Content-Type": "application/json"},
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
