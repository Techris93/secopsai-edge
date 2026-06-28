from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_pilot_mvp"
down_revision = "0002_scan_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sensors", sa.Column("version", sa.String(length=80)))
    op.add_column("sensors", sa.Column("os_name", sa.String(length=120)))
    op.add_column("sensors", sa.Column("last_error", sa.Text()))
    op.add_column("sensors", sa.Column("disabled_at", sa.DateTime(timezone=True)))

    op.create_table(
        "scan_schedules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("sensor_id", sa.String(length=36), sa.ForeignKey("sensors.id"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("target_cidr", sa.String(length=64), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("time_of_day", sa.String(length=5), nullable=False),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("day_of_week", sa.Integer()),
        sa.Column("include_wifi", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scan_schedules_enabled_next_run", "scan_schedules", ["enabled", "next_run_at"])

    op.add_column("scan_jobs", sa.Column("schedule_id", sa.String(length=36), sa.ForeignKey("scan_schedules.id")))
    op.create_index("ix_scan_jobs_schedule", "scan_jobs", ["schedule_id"])

    op.create_table(
        "finding_notes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("finding_id", sa.String(length=36), sa.ForeignKey("findings.id"), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_finding_notes_finding", "finding_notes", ["finding_id"])

    op.create_table(
        "notification_endpoints",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id")),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("target", sa.String(length=500), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notification_endpoints")
    op.drop_index("ix_finding_notes_finding", table_name="finding_notes")
    op.drop_table("finding_notes")
    op.drop_index("ix_scan_jobs_schedule", table_name="scan_jobs")
    op.drop_column("scan_jobs", "schedule_id")
    op.drop_index("ix_scan_schedules_enabled_next_run", table_name="scan_schedules")
    op.drop_table("scan_schedules")
    op.drop_column("sensors", "disabled_at")
    op.drop_column("sensors", "last_error")
    op.drop_column("sensors", "os_name")
    op.drop_column("sensors", "version")
