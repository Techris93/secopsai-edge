"""add organization tenancy boundaries

Revision ID: 0009_organizations
Revises: 0008_sensor_runtime_state
"""

from alembic import op
import sqlalchemy as sa
import uuid


revision = "0009_organizations"
down_revision = "0008_sensor_runtime_state"
branch_labels = None
depends_on = None

DEFAULT_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    organizations = sa.table(
        "organizations",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("active", sa.Boolean),
    )
    op.bulk_insert(
        organizations,
        [{"id": DEFAULT_ORGANIZATION_ID, "name": "Default Workspace", "slug": "default", "active": True}],
    )

    site_name_constraint = next(
        (
            item
            for item in sa.inspect(op.get_bind()).get_unique_constraints("sites")
            if item.get("column_names") == ["name"]
        ),
        None,
    )
    naming_convention = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
    with op.batch_alter_table("sites", naming_convention=naming_convention) as batch:
        batch.add_column(
            sa.Column(
                "organization_id",
                sa.String(length=36),
                nullable=False,
                server_default=DEFAULT_ORGANIZATION_ID,
            )
        )
        batch.create_foreign_key("fk_sites_organization", "organizations", ["organization_id"], ["id"])
        batch.create_index("ix_sites_organization_id", ["organization_id"])
        if site_name_constraint is not None:
            batch.drop_constraint(site_name_constraint.get("name") or "uq_sites_name", type_="unique")
        batch.create_unique_constraint("uq_site_org_name", ["organization_id", "name"])

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_membership"),
    )
    op.create_index(
        "ix_organization_memberships_user_active",
        "organization_memberships",
        ["user_id", "active"],
    )
    users = op.get_bind().execute(sa.text("SELECT id, role, active FROM users")).mappings().all()
    membership_rows = [
        {
            "id": str(uuid.uuid4()),
            "organization_id": DEFAULT_ORGANIZATION_ID,
            "user_id": row["id"],
            "role": row["role"],
            "active": row["active"],
        }
        for row in users
    ]
    if membership_rows:
        memberships = sa.table(
            "organization_memberships",
            sa.column("id", sa.String),
            sa.column("organization_id", sa.String),
            sa.column("user_id", sa.String),
            sa.column("role", sa.String),
            sa.column("active", sa.Boolean),
        )
        op.bulk_insert(memberships, membership_rows)

    for table_name in ("audit_logs", "notification_endpoints", "notification_deliveries"):
        with op.batch_alter_table(table_name) as batch:
            batch.add_column(
                sa.Column(
                    "organization_id",
                    sa.String(length=36),
                    nullable=False,
                    server_default=DEFAULT_ORGANIZATION_ID,
                )
            )
            batch.create_foreign_key(
                f"fk_{table_name}_organization", "organizations", ["organization_id"], ["id"]
            )
            batch.create_index(f"ix_{table_name}_organization_id", ["organization_id"])


def downgrade() -> None:
    for table_name in ("notification_deliveries", "notification_endpoints", "audit_logs"):
        with op.batch_alter_table(table_name) as batch:
            batch.drop_index(f"ix_{table_name}_organization_id")
            batch.drop_constraint(f"fk_{table_name}_organization", type_="foreignkey")
            batch.drop_column("organization_id")
    op.drop_index("ix_organization_memberships_user_active", table_name="organization_memberships")
    op.drop_table("organization_memberships")
    with op.batch_alter_table("sites", naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"}) as batch:
        batch.drop_constraint("uq_site_org_name", type_="unique")
        batch.create_unique_constraint("uq_sites_name", ["name"])
        batch.drop_index("ix_sites_organization_id")
        batch.drop_constraint("fk_sites_organization", type_="foreignkey")
        batch.drop_column("organization_id")
    op.drop_table("organizations")
