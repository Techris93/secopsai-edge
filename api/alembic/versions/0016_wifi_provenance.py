"""add Wi-Fi collection provenance

Revision ID: 0016_wifi_provenance
Revises: 0015_data_lifecycle
"""

from alembic import op
import sqlalchemy as sa


revision = "0016_wifi_provenance"
down_revision = "0015_data_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wifi_networks",
        sa.Column("source", sa.String(length=120), nullable=False, server_default="unknown"),
    )


def downgrade() -> None:
    op.drop_column("wifi_networks", "source")
