"""add durable audit for trusted authorization administration

Revision ID: 0012_authorization_admin_audit
Revises: 0011_tenant_scoped_rbac
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_authorization_admin_audit"
down_revision = "0011_tenant_scoped_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authorization_admin_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operator", sa.String(200), nullable=False),
        sa.Column("operation", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role_key", sa.String(80), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    op.create_index("ix_authorization_admin_audit_target_id", "authorization_admin_audit", ["target_id"])
    op.create_index("ix_authorization_admin_audit_actor_id", "authorization_admin_audit", ["actor_id"])
    op.create_index("ix_authorization_admin_audit_tenant_id", "authorization_admin_audit", ["tenant_id"])
    op.create_index("ix_authorization_admin_audit_correlation_id", "authorization_admin_audit", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_authorization_admin_audit_correlation_id", table_name="authorization_admin_audit")
    op.drop_index("ix_authorization_admin_audit_tenant_id", table_name="authorization_admin_audit")
    op.drop_index("ix_authorization_admin_audit_actor_id", table_name="authorization_admin_audit")
    op.drop_index("ix_authorization_admin_audit_target_id", table_name="authorization_admin_audit")
    op.drop_table("authorization_admin_audit")
