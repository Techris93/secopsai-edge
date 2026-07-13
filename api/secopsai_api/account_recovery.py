from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from secopsai_api.config import Settings, get_settings
from secopsai_api.models import AccountAccessToken, User, new_id, utcnow
from secopsai_api.notifications import send_email_message
from secopsai_api.security import constant_time_equals


PASSWORD_RESET_PURPOSE = "password_reset"
DELIVERABLE_STATUSES = {"queued", "retrying"}


def _timestamp(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


def _signature(token_id: str, user_id: str, expires_at: datetime, purpose: str, settings: Settings) -> str:
    payload = f"{purpose}:{token_id}:{user_id}:{_timestamp(expires_at)}".encode("utf-8")
    digest = hmac.new(settings.token_secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _token_hash(token: str, settings: Settings) -> str:
    return hmac.new(
        settings.token_secret.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def materialize_access_token(row: AccountAccessToken, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return ".".join(
        [
            "secopsai_access",
            row.id,
            str(_timestamp(row.expires_at)),
            _signature(row.id, row.user_id, row.expires_at, row.purpose, settings),
        ]
    )


def queue_password_reset(db: Session, user: User, settings: Settings | None = None) -> AccountAccessToken | None:
    settings = settings or get_settings()
    now = utcnow()
    cooldown_start = now - timedelta(seconds=max(1, settings.password_reset_cooldown_seconds))
    recent = db.scalar(
        select(AccountAccessToken).where(
            AccountAccessToken.user_id == user.id,
            AccountAccessToken.purpose == PASSWORD_RESET_PURPOSE,
            AccountAccessToken.used_at.is_(None),
            AccountAccessToken.created_at >= cooldown_start,
        )
    )
    if recent is not None:
        return None

    for existing in db.scalars(
        select(AccountAccessToken).where(
            AccountAccessToken.user_id == user.id,
            AccountAccessToken.purpose == PASSWORD_RESET_PURPOSE,
            AccountAccessToken.used_at.is_(None),
        )
    ).all():
        existing.used_at = now
        if existing.delivery_status in DELIVERABLE_STATUSES:
            existing.delivery_status = "failed"
            existing.delivery_detail = "Superseded by a newer password reset request"

    row = AccountAccessToken(
        id=new_id(),
        user_id=user.id,
        purpose=PASSWORD_RESET_PURPOSE,
        token_hash="pending",
        expires_at=now + timedelta(seconds=max(300, settings.password_reset_ttl_seconds)),
        max_delivery_attempts=max(1, settings.password_reset_max_delivery_attempts),
        next_attempt_at=now,
    )
    row.token_hash = _token_hash(materialize_access_token(row, settings), settings)
    db.add(row)
    db.flush()
    return row


def _reset_url(token: str, settings: Settings) -> str:
    raw = str(settings.dashboard_reset_url or "").strip()
    parsed = urlparse(raw)
    is_loopback = parsed.hostname in {"127.0.0.1", "localhost"}
    if parsed.scheme not in ({"http", "https"} if is_loopback else {"https"}) or not parsed.netloc:
        raise RuntimeError("SECOPSAI_DASHBOARD_RESET_URL must be an HTTPS URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("SECOPSAI_DASHBOARD_RESET_URL must not contain credentials, query, or fragment")
    return f"{raw}#reset_token={token}"


def _send_password_reset(row: AccountAccessToken, user: User, settings: Settings) -> tuple[bool, str]:
    try:
        token = materialize_access_token(row, settings)
        message = EmailMessage()
        message["Subject"] = "Reset your SecOpsAI Edge password"
        message["From"] = settings.smtp_from
        message["To"] = user.email
        message.set_content(
            "\n".join(
                [
                    "A password reset was requested for your SecOpsAI Edge operator account.",
                    "",
                    _reset_url(token, settings),
                    "",
                    f"This link expires in {max(5, settings.password_reset_ttl_seconds // 60)} minutes and can be used once.",
                    "If you did not request this, no action is required.",
                ]
            )
        )
        send_email_message(message, settings)
        return True, "Password reset email delivered"
    except Exception as exc:  # pragma: no cover - external service boundary
        return False, str(exc)


def attempt_account_access_delivery(
    db: Session,
    row: AccountAccessToken,
    *,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    if row.delivery_status not in DELIVERABLE_STATUSES:
        return
    now = utcnow()
    comparison_now = now if row.expires_at.tzinfo else now.replace(tzinfo=None)
    if row.used_at is not None or row.expires_at <= comparison_now:
        row.delivery_status = "failed"
        row.delivery_detail = "Access link expired or was already used"
        return
    user = db.get(User, row.user_id)
    if user is None or not user.active:
        row.delivery_status = "failed"
        row.delivery_detail = "Account is unavailable"
        return
    row.delivery_attempts += 1
    row.last_attempt_at = now
    ok, detail = _send_password_reset(row, user, settings)
    row.delivery_detail = detail[:2000]
    if ok:
        row.delivery_status = "delivered"
        row.delivered_at = now
    elif row.delivery_attempts >= row.max_delivery_attempts:
        row.delivery_status = "failed"
    else:
        row.delivery_status = "retrying"
        row.next_attempt_at = now + timedelta(seconds=min(60 * (5 ** (row.delivery_attempts - 1)), 3600))
    db.flush()


def process_due_account_access_deliveries(
    db: Session,
    *,
    settings: Settings | None = None,
    limit: int | None = None,
) -> dict[str, int]:
    settings = settings or get_settings()
    batch_size = max(1, min(limit or settings.password_reset_batch_size, 100))
    rows = db.scalars(
        select(AccountAccessToken)
        .where(
            AccountAccessToken.delivery_status.in_(DELIVERABLE_STATUSES),
            AccountAccessToken.next_attempt_at <= utcnow(),
        )
        .order_by(AccountAccessToken.next_attempt_at, AccountAccessToken.created_at)
        .limit(batch_size)
    ).all()
    totals = {"processed": 0, "delivered": 0, "retrying": 0, "failed": 0}
    for row in rows:
        attempt_account_access_delivery(db, row, settings=settings)
        totals["processed"] += 1
        totals[row.delivery_status] += 1
    db.flush()
    return totals


def consume_password_reset(
    db: Session,
    token: str,
    new_password: str,
    *,
    settings: Settings | None = None,
) -> User | None:
    settings = settings or get_settings()
    row = db.scalar(
        select(AccountAccessToken).where(
            AccountAccessToken.token_hash == _token_hash(token, settings),
            AccountAccessToken.purpose == PASSWORD_RESET_PURPOSE,
        )
    )
    if row is None or row.used_at is not None:
        return None
    now = utcnow()
    comparison_now = now if row.expires_at.tzinfo else now.replace(tzinfo=None)
    if row.expires_at <= comparison_now:
        row.used_at = now
        return None
    expected = materialize_access_token(row, settings)
    if not constant_time_equals(token, expected):
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.active:
        return None

    from secopsai_api.security import hash_password

    user.password_hash = hash_password(new_password)
    user.password_changed_at = now
    user.failed_login_count = 0
    user.locked_until = None
    user.session_version += 1
    for active in db.scalars(
        select(AccountAccessToken).where(
            AccountAccessToken.user_id == user.id,
            AccountAccessToken.purpose == PASSWORD_RESET_PURPOSE,
            AccountAccessToken.used_at.is_(None),
        )
    ).all():
        active.used_at = now
    db.flush()
    return user
