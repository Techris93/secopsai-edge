"""add sensor runtime state

Revision ID: 0008_sensor_runtime_state
Revises: 0007_user_lifecycle
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_sensor_runtime_state"
down_revision = "0007_user_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sensors", sa.Column("worker_state", sa.String(length=40)))
    op.add_column("sensors", sa.Column("current_job_id", sa.String(length=36)))


def downgrade() -> None:
    op.drop_column("sensors", "current_job_id")
    op.drop_column("sensors", "worker_state")
