from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from secopsai_api.config import get_settings
from secopsai_api.database import get_db
from secopsai_api.models import DEFAULT_ORGANIZATION_ID, IntegrationToken, Organization, Sensor, User, utcnow
from secopsai_api.tenancy import ensure_default_membership, ensure_default_tenant_state, membership_for_user


bearer = HTTPBearer(auto_error=False)
DASHBOARD_SESSION_PREFIX = "secopsai_session"
INTEGRATION_TOKEN_PREFIX = "secopsai_integration_"
LEGACY_INTEGRATION_TOKEN_PREFIX = "secopsai_core_"
INTEGRATION_TOKEN_PREFIXES = (INTEGRATION_TOKEN_PREFIX, LEGACY_INTEGRATION_TOKEN_PREFIX)
PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 260_000
DUMMY_PASSWORD_HASH = f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}$secopsai-dummy$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def generate_sensor_token() -> str:
    return secrets.token_urlsafe(32)


def generate_integration_token() -> str:
    return f"{INTEGRATION_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def hash_secret(secret: str) -> str:
    settings = get_settings()
    return hmac.new(
        settings.token_secret.encode("utf-8"),
        secret.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def hash_password(password: str) -> str:
    salt = secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}${salt}${_b64url_encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        prefix, iterations_raw, salt, expected = password_hash.split("$", 3)
        iterations = int(iterations_raw)
    except ValueError:
        return False
    if prefix != PASSWORD_HASH_PREFIX:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return constant_time_equals(_b64url_encode(digest), expected)


def create_dashboard_session(
    subject: str = "dashboard",
    role: str = "admin",
    user_id: str | None = None,
    session_version: int | None = None,
    organization_id: str = DEFAULT_ORGANIZATION_ID,
) -> str:
    settings = get_settings()
    payload = {
        "sub": subject,
        "role": role,
        "exp": int(time.time()) + settings.dashboard_session_ttl_seconds,
        "nonce": secrets.token_urlsafe(12),
        "org": organization_id,
    }
    if user_id:
        payload["uid"] = user_id
        payload["ver"] = session_version if session_version is not None else 1
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(payload_part)
    return f"{DASHBOARD_SESSION_PREFIX}.{payload_part}.{signature}"


def decode_dashboard_session(token: str) -> dict[str, Any] | None:
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != DASHBOARD_SESSION_PREFIX:
        return None

    payload_part = parts[1]
    signature = parts[2]
    if not constant_time_equals(signature, _sign(payload_part)):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_part))
    except (ValueError, json.JSONDecodeError):
        return None

    if not payload.get("sub"):
        return None
    try:
        expires_at = int(payload["exp"])
    except (KeyError, TypeError, ValueError):
        return None
    if expires_at <= int(time.time()):
        return None
    return payload if isinstance(payload, dict) else None


def verify_dashboard_session(token: str) -> bool:
    return decode_dashboard_session(token) is not None


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    context = get_dashboard_auth_context(credentials, db)
    if str(context.get("role") or "").lower() not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    return context


def require_operator(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_dashboard_auth_context(credentials, db)


def require_core_export_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    credential = credentials.credentials
    if credential.startswith(INTEGRATION_TOKEN_PREFIXES):
        return authenticate_integration_token(db, credential, "core:export")

    context = get_dashboard_auth_context(credentials, db)
    if str(context.get("role") or "").lower() not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    return context


def require_operations_read_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    credential = credentials.credentials
    if credential.startswith(INTEGRATION_TOKEN_PREFIXES):
        return authenticate_integration_token(db, credential, "operations:read")
    return get_dashboard_auth_context(credentials, db)


def require_integration_token_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    credential = credentials.credentials
    if not credential.startswith(INTEGRATION_TOKEN_PREFIXES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Integration token required")
    return authenticate_integration_token(db, credential)


def authenticate_integration_token(
    db: Session,
    credential: str,
    required_scope: str | None = None,
) -> dict[str, Any]:
    token = db.scalar(
        select(IntegrationToken).where(IntegrationToken.token_hash == hash_secret(credential))
    )
    now = utcnow()
    if token is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid integration token")
    comparison_now = now
    if token.expires_at.tzinfo is None:
        comparison_now = now.replace(tzinfo=None)
    organization = db.get(Organization, token.organization_id)
    if (
        token.revoked_at is not None
        or token.expires_at <= comparison_now
        or (required_scope is not None and required_scope not in (token.scopes or []))
        or organization is None
        or not organization.active
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid integration token")
    token.last_used_at = now
    db.commit()
    return {
        "sub": f"integration-token:{token.id}",
        "role": "integration",
        "org": token.organization_id,
        "scopes": list(token.scopes or []),
        "integration_token_id": token.id,
    }


def get_dashboard_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin token")
    credential = credentials.credentials
    if constant_time_equals(credential, settings.admin_token):
        ensure_default_tenant_state(db)
        return {
            "sub": "admin-token",
            "role": "admin",
            "org": DEFAULT_ORGANIZATION_ID,
            "legacy": True,
        }
    session = decode_dashboard_session(credential)
    if session is not None:
        user_id = session.get("uid")
        if user_id:
            user = db.get(User, user_id)
            if user is None or not user.active or int(session.get("ver", 0)) != user.session_version:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard session revoked")
            organization_id = str(session.get("org") or DEFAULT_ORGANIZATION_ID)
            membership = membership_for_user(db, user.id, organization_id)
            if membership is None and "org" not in session:
                membership = ensure_default_membership(db, user)
                db.commit()
            if membership is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access revoked")
            session["sub"] = user.email
            session["role"] = membership.role
            session["org"] = membership.organization_id
        return session
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")


def authenticate_sensor(db: Session, sensor_id: str, sensor_token: str | None) -> Sensor:
    if not sensor_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing sensor token")
    sensor = db.get(Sensor, sensor_id)
    if sensor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    if not constant_time_equals(sensor.token_hash, hash_secret(sensor_token)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid sensor token")
    return sensor


def require_sensor_for_path(
    sensor_id: str,
    x_sensor_token: str | None = Header(default=None, alias="X-Sensor-Token"),
    db: Session = Depends(get_db),
) -> Sensor:
    return authenticate_sensor(db, sensor_id, x_sensor_token)


def _sign(value: str) -> str:
    settings = get_settings()
    digest = hmac.new(
        settings.token_secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64url_encode(digest)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> str:
    padded = value + ("=" * ((4 - len(value) % 4) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
