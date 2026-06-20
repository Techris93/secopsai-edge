from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "sensors",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("hostname", sa.String(length=255)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "scan_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("sensor_id", sa.String(length=36), sa.ForeignKey("sensors.id"), nullable=False),
        sa.Column("target_cidr", sa.String(length=64)),
        sa.Column("scan_source", sa.String(length=120)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("summary", sa.JSON(), nullable=False),
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("mac_address", sa.String(length=32)),
        sa.Column("vendor", sa.String(length=160)),
        sa.Column("hostname", sa.String(length=255)),
        sa.Column("os_guess", sa.String(length=120)),
        sa.Column("device_type", sa.String(length=80)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("site_id", "ip_address", name="uq_asset_site_ip"),
    )
    op.create_table(
        "asset_observations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("sensor_id", sa.String(length=36), sa.ForeignKey("sensors.id"), nullable=False),
        sa.Column("scan_id", sa.String(length=36), sa.ForeignKey("scan_runs.id"), nullable=False),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("mac_address", sa.String(length=32)),
        sa.Column("vendor", sa.String(length=160)),
        sa.Column("hostname", sa.String(length=255)),
        sa.Column("os_guess", sa.String(length=120)),
        sa.Column("raw_source", sa.String(length=80)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw", sa.JSON(), nullable=False),
    )
    op.create_table(
        "services",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=120)),
        sa.Column("product", sa.String(length=160)),
        sa.Column("version", sa.String(length=120)),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("asset_id", "port", "protocol", name="uq_service_asset_port_proto"),
    )
    op.create_table(
        "wifi_networks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("sensor_id", sa.String(length=36), sa.ForeignKey("sensors.id"), nullable=False),
        sa.Column("ssid", sa.String(length=160), nullable=False),
        sa.Column("bssid", sa.String(length=32)),
        sa.Column("channel", sa.Integer()),
        sa.Column("signal", sa.Float()),
        sa.Column("encryption", sa.String(length=160)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("site_id", "ssid", "bssid", name="uq_wifi_site_ssid_bssid"),
    )
    op.create_table(
        "findings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id")),
        sa.Column("wifi_network_id", sa.String(length=36), sa.ForeignKey("wifi_networks.id")),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("mitre_attack", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("sensor_id", sa.String(length=36), sa.ForeignKey("sensors.id")),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=80)),
        sa.Column("resource_id", sa.String(length=80)),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("reports")
    op.drop_table("findings")
    op.drop_table("wifi_networks")
    op.drop_table("services")
    op.drop_table("asset_observations")
    op.drop_table("assets")
    op.drop_table("scan_runs")
    op.drop_table("sensors")
    op.drop_table("users")
    op.drop_table("sites")
