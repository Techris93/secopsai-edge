"""add durable account recovery tokens

Revision ID: 0013_account_recovery
Revises: 0012_integration_tokens
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_account_recovery"
down_revision = "0012_integration_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_access_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("delivery_status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_delivery_attempts", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("delivery_detail", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_account_access_tokens_due", "account_access_tokens", ["delivery_status", "next_attempt_at"])
    op.create_index("ix_account_access_tokens_user_created", "account_access_tokens", ["user_id", "created_at"])
    op.create_index("ix_account_access_tokens_hash", "account_access_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_account_access_tokens_hash", table_name="account_access_tokens")
    op.drop_index("ix_account_access_tokens_user_created", table_name="account_access_tokens")
    op.drop_index("ix_account_access_tokens_due", table_name="account_access_tokens")
    op.drop_table("account_access_tokens")
