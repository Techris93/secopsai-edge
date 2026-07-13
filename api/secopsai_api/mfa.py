from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from secopsai_api.config import Settings, get_settings
from secopsai_api.models import MfaRecoveryCode, User, new_id, utcnow
from secopsai_api.security import constant_time_equals


MFA_CHALLENGE_PREFIX = "secopsai_mfa"
MFA_ISSUER = "SecOpsAI Edge"
TOTP_PERIOD_SECONDS = 30
TOTP_DIGITS = 6


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padded = value + ("=" * ((4 - len(value) % 4) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _encryption_key(settings: Settings) -> bytes:
    return hashlib.sha256(
        f"secopsai-mfa-v1:{settings.mfa_encryption_key}".encode("utf-8")
    ).digest()


def encrypt_secret(secret: str, user_id: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_encryption_key(settings)).encrypt(
        nonce,
        secret.encode("ascii"),
        user_id.encode("utf-8"),
    )
    return f"v1.{_b64url_encode(nonce + ciphertext)}"


def decrypt_secret(ciphertext: str, user_id: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    try:
        version, encoded = ciphertext.split(".", 1)
        if version != "v1":
            raise ValueError("unsupported MFA secret format")
        payload = _b64url_decode(encoded)
        return AESGCM(_encryption_key(settings)).decrypt(
            payload[:12],
            payload[12:],
            user_id.encode("utf-8"),
        ).decode("ascii")
    except (InvalidTag, UnicodeDecodeError, ValueError) as exc:
        raise RuntimeError("MFA secret cannot be decrypted") from exc


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _secret_bytes(secret: str) -> bytes:
    normalized = secret.strip().upper()
    padded = normalized + ("=" * ((8 - len(normalized) % 8) % 8))
    return base64.b32decode(padded.encode("ascii"), casefold=True)


def totp_at_counter(secret: str, counter: int) -> str:
    digest = hmac.new(
        _secret_bytes(secret),
        struct.pack(">Q", counter),
        hashlib.sha1,
    ).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**TOTP_DIGITS)).zfill(TOTP_DIGITS)


def current_totp(secret: str, *, at_time: int | None = None) -> str:
    timestamp = int(time.time()) if at_time is None else at_time
    return totp_at_counter(secret, timestamp // TOTP_PERIOD_SECONDS)


def verify_totp(
    secret: str,
    code: str,
    *,
    last_counter: int | None = None,
    at_time: int | None = None,
) -> int | None:
    normalized = "".join(character for character in code if character.isdigit())
    if len(normalized) != TOTP_DIGITS:
        return None
    timestamp = int(time.time()) if at_time is None else at_time
    current_counter = timestamp // TOTP_PERIOD_SECONDS
    for counter in range(current_counter - 1, current_counter + 2):
        if last_counter is not None and counter <= last_counter:
            continue
        if constant_time_equals(normalized, totp_at_counter(secret, counter)):
            return counter
    return None


def provisioning_uri(secret: str, email: str) -> str:
    label = quote(f"{MFA_ISSUER}:{email}", safe="")
    issuer = quote(MFA_ISSUER, safe="")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={issuer}"
        f"&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_PERIOD_SECONDS}"
    )


def begin_mfa_setup(user: User, settings: Settings | None = None) -> tuple[str, str]:
    settings = settings or get_settings()
    secret = generate_totp_secret()
    user.mfa_pending_secret_ciphertext = encrypt_secret(secret, user.id, settings)
    user.mfa_pending_expires_at = utcnow() + timedelta(
        seconds=max(300, settings.mfa_setup_ttl_seconds)
    )
    return secret, provisioning_uri(secret, user.email)


def _recovery_hash(code: str, user_id: str, settings: Settings) -> str:
    normalized = "".join(character for character in code.upper() if character.isalnum())
    return hmac.new(
        settings.mfa_encryption_key.encode("utf-8"),
        f"mfa-recovery:{user_id}:{normalized}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def replace_recovery_codes(
    db: Session,
    user: User,
    settings: Settings | None = None,
) -> list[str]:
    settings = settings or get_settings()
    db.execute(delete(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user.id))
    codes: list[str] = []
    for _ in range(10):
        compact = base64.b32encode(secrets.token_bytes(7)).decode("ascii").rstrip("=")[:10]
        code = f"{compact[:5]}-{compact[5:]}"
        codes.append(code)
        db.add(
            MfaRecoveryCode(
                id=new_id(),
                user_id=user.id,
                code_hash=_recovery_hash(code, user.id, settings),
            )
        )
    db.flush()
    return codes


def enable_mfa(
    db: Session,
    user: User,
    code: str,
    settings: Settings | None = None,
    *,
    at_time: int | None = None,
) -> list[str] | None:
    settings = settings or get_settings()
    if not user.mfa_pending_secret_ciphertext or not user.mfa_pending_expires_at:
        return None
    now = utcnow()
    comparison_now = now if user.mfa_pending_expires_at.tzinfo else now.replace(tzinfo=None)
    if user.mfa_pending_expires_at <= comparison_now:
        user.mfa_pending_secret_ciphertext = None
        user.mfa_pending_expires_at = None
        return None
    secret = decrypt_secret(user.mfa_pending_secret_ciphertext, user.id, settings)
    counter = verify_totp(secret, code, at_time=at_time)
    if counter is None:
        return None
    user.mfa_secret_ciphertext = user.mfa_pending_secret_ciphertext
    user.mfa_pending_secret_ciphertext = None
    user.mfa_pending_expires_at = None
    user.mfa_enabled_at = now
    user.mfa_last_counter = counter
    user.session_version += 1
    return replace_recovery_codes(db, user, settings)


def verify_mfa_code(
    db: Session,
    user: User,
    code: str,
    settings: Settings | None = None,
    *,
    at_time: int | None = None,
) -> bool:
    settings = settings or get_settings()
    if not user.mfa_secret_ciphertext or not user.mfa_enabled_at:
        return False
    secret = decrypt_secret(user.mfa_secret_ciphertext, user.id, settings)
    counter = verify_totp(
        secret,
        code,
        last_counter=user.mfa_last_counter,
        at_time=at_time,
    )
    if counter is not None:
        user.mfa_last_counter = counter
        db.flush()
        return True

    code_hash = _recovery_hash(code, user.id, settings)
    recovery = db.scalar(
        select(MfaRecoveryCode).where(
            MfaRecoveryCode.user_id == user.id,
            MfaRecoveryCode.code_hash == code_hash,
            MfaRecoveryCode.used_at.is_(None),
        )
    )
    if recovery is None:
        return False
    recovery.used_at = utcnow()
    db.flush()
    return True


def disable_mfa(db: Session, user: User) -> None:
    user.mfa_secret_ciphertext = None
    user.mfa_pending_secret_ciphertext = None
    user.mfa_pending_expires_at = None
    user.mfa_enabled_at = None
    user.mfa_last_counter = None
    user.session_version += 1
    db.execute(delete(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user.id))
    db.flush()


def create_mfa_challenge(
    user: User,
    organization_id: str,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    payload = {
        "uid": user.id,
        "org": organization_id,
        "ver": user.session_version,
        "exp": int(time.time()) + max(60, settings.mfa_challenge_ttl_seconds),
        "nonce": secrets.token_urlsafe(12),
    }
    encoded = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        settings.token_secret.encode("utf-8"),
        f"{MFA_CHALLENGE_PREFIX}.{encoded}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{MFA_CHALLENGE_PREFIX}.{encoded}.{_b64url_encode(signature)}"


def decode_mfa_challenge(
    token: str,
    settings: Settings | None = None,
) -> dict[str, object] | None:
    settings = settings or get_settings()
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != MFA_CHALLENGE_PREFIX:
        return None
    expected = hmac.new(
        settings.token_secret.encode("utf-8"),
        f"{parts[0]}.{parts[1]}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    try:
        supplied = _b64url_decode(parts[2])
        if not hmac.compare_digest(supplied, expected):
            return None
        payload = json.loads(_b64url_decode(parts[1]))
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) <= int(time.time()):
            return None
        if not payload.get("uid") or not payload.get("org"):
            return None
        return payload
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
