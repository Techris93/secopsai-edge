from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from secopsai_api.config import get_settings
from secopsai_api.database import get_db
from secopsai_api.models import Sensor


bearer = HTTPBearer(auto_error=False)
DASHBOARD_SESSION_PREFIX = "secopsai_session"


def generate_sensor_token() -> str:
    return secrets.token_urlsafe(32)


def hash_secret(secret: str) -> str:
    settings = get_settings()
    return hmac.new(
        settings.token_secret.encode("utf-8"),
        secret.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def create_dashboard_session() -> str:
    settings = get_settings()
    payload = {
        "sub": "dashboard",
        "exp": int(time.time()) + settings.dashboard_session_ttl_seconds,
        "nonce": secrets.token_urlsafe(12),
    }
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(payload_part)
    return f"{DASHBOARD_SESSION_PREFIX}.{payload_part}.{signature}"


def verify_dashboard_session(token: str) -> bool:
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != DASHBOARD_SESSION_PREFIX:
        return False

    payload_part = parts[1]
    signature = parts[2]
    if not constant_time_equals(signature, _sign(payload_part)):
        return False

    try:
        payload = json.loads(_b64url_decode(payload_part))
    except (ValueError, json.JSONDecodeError):
        return False

    if payload.get("sub") != "dashboard":
        return False
    try:
        expires_at = int(payload["exp"])
    except (KeyError, TypeError, ValueError):
        return False
    return expires_at > int(time.time())


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> None:
    settings = get_settings()
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin token")
    credential = credentials.credentials
    if constant_time_equals(credential, settings.admin_token) or verify_dashboard_session(credential):
        return
    else:
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
