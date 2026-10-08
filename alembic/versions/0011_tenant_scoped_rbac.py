"""add tenant-scoped RBAC and link external identities to actors

Revision ID: 0011_tenant_scoped_rbac
Revises: 0010_external_identity_mappings
"""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_tenant_scoped_rbac"
down_revision = "0010_external_identity_mappings"
branch_labels = None
depends_on = None

PERMISSIONS = (
    "CREATE_CASE", "TRIAGE_CASE", "START_ANALYSIS", "SUBMIT_OPTIONS", "AWAIT_DECISION",
    "MAKE_DECISION", "APPROVE_DECISION", "REJECT_DECISION", "CREATE_ACTION", "START_ACTION",
    "UPDATE_EXECUTION", "RECONCILE_EXECUTION", "CREATE_OUTCOME", "VERIFY_OUTCOME",
    "CREATE_EVIDENCE", "ADD_ANALYSIS",
)
ROLE_PERMISSIONS = {
    "tenant_admin": PERMISSIONS,
    "decision_author": (
        "CREATE_CASE", "TRIAGE_CASE", "START_ANALYSIS", "SUBMIT_OPTIONS", "AWAIT_DECISION",
        "CREATE_EVIDENCE", "ADD_ANALYSIS",
    ),
    "approver": ("MAKE_DECISION", "APPROVE_DECISION", "REJECT_DECISION"),
    "operator": (
        "CREATE_ACTION", "START_ACTION", "UPDATE_EXECUTION", "RECONCILE_EXECUTION",
        "CREATE_OUTCOME", "VERIFY_OUTCOME",
    ),
    "read_only_reviewer": (),
}
ROLES = (
    ("tenant_admin", "Tenant Admin"),
    ("decision_author", "Decision Author"),
    ("approver", "Approver"),
    ("operator", "Operator"),
    ("read_only_reviewer", "Read-only Reviewer"),
)


def upgrade() -> None:
    op.create_table(
        "actors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.execute(
        "INSERT INTO actors (id, is_active) "
        "SELECT DISTINCT actor_id, TRUE FROM external_identity_mappings"
    )
    op.create_table(
        "tenant_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("actor_id", "tenant_id", name="uq_tenant_membership_actor_tenant"),
    )
    op.create_index("ix_tenant_memberships_actor_id", "tenant_memberships", ["actor_id"])
    op.create_index("ix_tenant_memberships_tenant_id", "tenant_memberships", ["tenant_id"])
    op.create_table(
        "authorization_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "authorization_role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("authorization_roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("permission", sa.String(80), nullable=False),
        sa.UniqueConstraint("role_id", "permission", name="uq_authorization_role_permission"),
    )
    op.create_index("ix_authorization_role_permissions_role_id", "authorization_role_permissions", ["role_id"])
    op.create_table(
        "membership_role_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant_memberships.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("authorization_roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("membership_id", "role_id", name="uq_membership_role_assignment"),
    )
    op.create_index("ix_membership_role_assignments_membership_id", "membership_role_assignments", ["membership_id"])
    op.create_index("ix_membership_role_assignments_role_id", "membership_role_assignments", ["role_id"])

    # No memberships or role assignments are auto-created; the migration must not grant access.
    role_ids = {}
    for key, name in ROLES:
        role_id = uuid4()
        role_ids[key] = role_id
        op.execute(
            sa.text(
                "INSERT INTO authorization_roles (id, key, name, is_active) "
                "VALUES (:id, :key, :name, TRUE)"
            ).bindparams(id=role_id, key=key, name=name)
        )
    for role_key, permissions in ROLE_PERMISSIONS.items():
        for permission in permissions:
            op.execute(
                sa.text(
                    "INSERT INTO authorization_role_permissions (id, role_id, permission) "
                    "VALUES (:id, :role_id, :permission)"
                ).bindparams(id=uuid4(), role_id=role_ids[role_key], permission=permission)
            )

    op.create_foreign_key(
        "fk_external_identity_mappings_actor_id_actors",
        "external_identity_mappings",
        "actors",
        ["actor_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_external_identity_mappings_actor_id_actors",
        "external_identity_mappings",
        type_="foreignkey",
    )
    op.drop_index("ix_membership_role_assignments_role_id", table_name="membership_role_assignments")
    op.drop_index("ix_membership_role_assignments_membership_id", table_name="membership_role_assignments")
    op.drop_table("membership_role_assignments")
    op.drop_index("ix_authorization_role_permissions_role_id", table_name="authorization_role_permissions")
    op.drop_table("authorization_role_permissions")
    op.drop_table("authorization_roles")
    op.drop_index("ix_tenant_memberships_tenant_id", table_name="tenant_memberships")
    op.drop_index("ix_tenant_memberships_actor_id", table_name="tenant_memberships")
    op.drop_table("tenant_memberships")
    op.drop_table("actors")
