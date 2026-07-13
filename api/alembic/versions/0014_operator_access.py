"""add operator invitations and multi-factor authentication

Revision ID: 0014_operator_access
Revises: 0013_account_recovery
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_operator_access"
down_revision = "0013_account_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_ready", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("users", sa.Column("mfa_secret_ciphertext", sa.Text()))
    op.add_column("users", sa.Column("mfa_pending_secret_ciphertext", sa.Text()))
    op.add_column("users", sa.Column("mfa_pending_expires_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("mfa_enabled_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("mfa_last_counter", sa.Integer()))

    op.add_column(
        "account_access_tokens",
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id")),
    )
    op.add_column(
        "account_access_tokens",
        sa.Column("context", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )

    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_mfa_recovery_codes_user", "mfa_recovery_codes", ["user_id"])
    op.create_index(
        "ix_mfa_recovery_codes_hash",
        "mfa_recovery_codes",
        ["code_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_mfa_recovery_codes_hash", table_name="mfa_recovery_codes")
    op.drop_index("ix_mfa_recovery_codes_user", table_name="mfa_recovery_codes")
    op.drop_table("mfa_recovery_codes")
    op.drop_column("account_access_tokens", "context")
    op.drop_column("account_access_tokens", "organization_id")
    op.drop_column("users", "mfa_last_counter")
    op.drop_column("users", "mfa_enabled_at")
    op.drop_column("users", "mfa_pending_expires_at")
    op.drop_column("users", "mfa_pending_secret_ciphertext")
    op.drop_column("users", "mfa_secret_ciphertext")
    op.drop_column("users", "password_ready")
