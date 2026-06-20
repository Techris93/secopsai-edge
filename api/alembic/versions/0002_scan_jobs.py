from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_scan_jobs"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scan_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("sensor_id", sa.String(length=36), sa.ForeignKey("sensors.id"), nullable=False),
        sa.Column("target_cidr", sa.String(length=64), nullable=False),
        sa.Column("include_wifi", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("preview", sa.JSON(), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text()),
    )
    op.create_index("ix_scan_jobs_sensor_status", "scan_jobs", ["sensor_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_scan_jobs_sensor_status", table_name="scan_jobs")
    op.drop_table("scan_jobs")
