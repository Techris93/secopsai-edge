"""add durable notification deliveries

Revision ID: 0006_notification_delivery
Revises: 0005_auth_lockout
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_notification_delivery"
down_revision = "0005_auth_lockout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "endpoint_id",
            sa.String(length=36),
            sa.ForeignKey("notification_endpoints.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id")),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("response_detail", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_notification_deliveries_due",
        "notification_deliveries",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "ix_notification_deliveries_endpoint_created",
        "notification_deliveries",
        ["endpoint_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_deliveries_endpoint_created", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_due", table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
