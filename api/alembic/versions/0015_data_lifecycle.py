"""add organization data lifecycle policies

Revision ID: 0015_data_lifecycle
Revises: 0014_operator_access
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_data_lifecycle"
down_revision = "0014_operator_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_lifecycle_policies",
        sa.Column(
            "organization_id",
            sa.String(length=36),
            sa.ForeignKey("organizations.id"),
            primary_key=True,
        ),
        sa.Column("observation_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("scan_history_days", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("notification_delivery_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("account_access_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("credential_history_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("report_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("audit_log_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("data_lifecycle_policies")
