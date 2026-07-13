from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from secopsai_api.models import (
    DEFAULT_ORGANIZATION_ID,
    Organization,
    OrganizationMembership,
    Site,
    User,
    utcnow,
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:120] or "workspace"


def unique_slug(db: Session, name: str) -> str:
    base = slugify(name)
    candidate = base
    suffix = 2
    while db.scalar(select(Organization.id).where(Organization.slug == candidate)):
        candidate = f"{base[: max(1, 116 - len(str(suffix)))]}-{suffix}"
        suffix += 1
    return candidate


def ensure_default_organization(db: Session) -> Organization:
    organization = db.get(Organization, DEFAULT_ORGANIZATION_ID)
    if organization is None:
        organization = Organization(
            id=DEFAULT_ORGANIZATION_ID,
            name="Default Workspace",
            slug="default",
            active=True,
        )
        db.add(organization)
        db.flush()
    return organization


def ensure_default_membership(db: Session, user: User) -> OrganizationMembership:
    ensure_default_organization(db)
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == DEFAULT_ORGANIZATION_ID,
            OrganizationMembership.user_id == user.id,
        )
    )
    if membership is None:
        membership = OrganizationMembership(
            organization_id=DEFAULT_ORGANIZATION_ID,
            user_id=user.id,
            role=user.role,
            active=user.active,
        )
        db.add(membership)
        db.flush()
    return membership


def ensure_default_tenant_state(db: Session) -> Organization:
    organization = ensure_default_organization(db)
    for user in db.scalars(select(User)).all():
        ensure_default_membership(db, user)
    db.flush()
    return organization


def membership_for_user(
    db: Session,
    user_id: str,
    organization_id: str | None = None,
) -> OrganizationMembership | None:
    query = (
        select(OrganizationMembership)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.active.is_(True),
            Organization.active.is_(True),
        )
        .order_by(OrganizationMembership.created_at.asc())
    )
    if organization_id:
        query = query.where(OrganizationMembership.organization_id == organization_id)
    return db.scalar(query)


def organization_id_from_context(context: dict[str, Any]) -> str:
    value = context.get("org")
    if not isinstance(value, str) or not value:
        return DEFAULT_ORGANIZATION_ID
    return value


def site_for_organization(db: Session, site_id: str, organization_id: str) -> Site:
    site = db.scalar(
        select(Site).where(Site.id == site_id, Site.organization_id == organization_id)
    )
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


def require_active_organization(db: Session, organization_id: str) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None or not organization.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace unavailable")
    return organization


def count_active_workspace_admins(db: Session, organization_id: str, *, exclude_user_id: str | None = None) -> int:
    query = select(func.count(OrganizationMembership.id)).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.active.is_(True),
        OrganizationMembership.role.in_(["owner", "admin"]),
    )
    if exclude_user_id:
        query = query.where(OrganizationMembership.user_id != exclude_user_id)
    return int(db.scalar(query) or 0)


def touch_membership(membership: OrganizationMembership) -> None:
    membership.updated_at = utcnow()
