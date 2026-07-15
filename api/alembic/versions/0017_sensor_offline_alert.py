"""track sensor offline notification deduplication

Revision ID: 0017_sensor_offline_alert
Revises: 0016_wifi_provenance
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_sensor_offline_alert"
down_revision = "0016_wifi_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sensors",
        sa.Column("offline_alerted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sensors", "offline_alerted_at")
