"""add approved baseline rules

Revision ID: 0004_baseline_rules
Revises: 0003_pilot_mvp
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_baseline_rules"
down_revision = "0003_pilot_mvp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "baseline_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("site_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("matcher", sa.JSON(), nullable=False),
        sa.Column("finding_types", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_baseline_rules_site_kind_status",
        "baseline_rules",
        ["site_id", "kind", "status"],
        unique=False,
    )
    op.create_index("ix_baseline_rules_expires_at", "baseline_rules", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_baseline_rules_expires_at", table_name="baseline_rules")
    op.drop_index("ix_baseline_rules_site_kind_status", table_name="baseline_rules")
    op.drop_table("baseline_rules")
