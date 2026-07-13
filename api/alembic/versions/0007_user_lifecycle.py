"""add user lifecycle and session revocation state

Revision ID: 0007_user_lifecycle
Revises: 0006_notification_delivery
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_user_lifecycle"
down_revision = "0006_notification_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("session_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "session_version")
    op.drop_column("users", "active")
