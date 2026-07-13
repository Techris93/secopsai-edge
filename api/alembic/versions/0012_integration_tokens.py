"""add workspace-scoped integration tokens

Revision ID: 0012_integration_tokens
Revises: 0011_schema_alignment
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_integration_tokens"
down_revision = "0011_schema_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_integration_tokens_org_created",
        "integration_tokens",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_integration_tokens_token_hash",
        "integration_tokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_integration_tokens_token_hash", table_name="integration_tokens")
    op.drop_index("ix_integration_tokens_org_created", table_name="integration_tokens")
    op.drop_table("integration_tokens")
