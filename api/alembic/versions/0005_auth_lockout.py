"""add dashboard login lockout state

Revision ID: 0005_auth_lockout
Revises: 0004_baseline_rules
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_auth_lockout"
down_revision = "0004_baseline_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
