"""align operational indexes with ORM metadata

Revision ID: 0011_schema_alignment
Revises: 0010_sensor_enrollments
"""

from alembic import op


revision = "0011_schema_alignment"
down_revision = "0010_sensor_enrollments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_assets_mac_address", "assets", ["mac_address"])


def downgrade() -> None:
    op.drop_index("ix_assets_mac_address", table_name="assets")
