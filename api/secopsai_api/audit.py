from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from secopsai_api.models import AuditLog


def write_audit(
    db: Session,
    action: str,
    *,
    sensor_id: str | None = None,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            sensor_id=sensor_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
    )
