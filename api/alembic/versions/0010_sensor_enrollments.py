"""add one-time sensor enrollments

Revision ID: 0010_sensor_enrollments
Revises: 0009_organizations
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_sensor_enrollments"
down_revision = "0009_organizations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sensor_enrollments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_sensor_enrollments_org_created",
        "sensor_enrollments",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_sensor_enrollments_token_hash",
        "sensor_enrollments",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_sensor_enrollments_token_hash", table_name="sensor_enrollments")
    op.drop_index("ix_sensor_enrollments_org_created", table_name="sensor_enrollments")
    op.drop_table("sensor_enrollments")
