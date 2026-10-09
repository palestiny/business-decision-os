"""add durable audit for authorization allow/deny decisions

Revision ID: 0014_authorization_decision_audit
Revises: 0013_separation_of_duties
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_authorization_decision_audit"
down_revision = "0013_separation_of_duties"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authorization_decision_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission", sa.String(80), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", sa.String(8), nullable=False),
        sa.Column("reason_code", sa.String(80), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("outcome IN ('ALLOW', 'DENY')", name="ck_authorization_decision_audit_outcome"),
    )
    op.create_index("ix_authorization_decision_audit_tenant_time", "authorization_decision_audit", ["tenant_id", "occurred_at"])
    op.create_index("ix_authorization_decision_audit_actor_time", "authorization_decision_audit", ["actor_id", "occurred_at"])
    op.create_index("ix_authorization_decision_audit_resource", "authorization_decision_audit", ["resource_id"])
    op.create_index("ix_authorization_decision_audit_correlation_id", "authorization_decision_audit", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_authorization_decision_audit_correlation_id", table_name="authorization_decision_audit")
    op.drop_index("ix_authorization_decision_audit_resource", table_name="authorization_decision_audit")
    op.drop_index("ix_authorization_decision_audit_actor_time", table_name="authorization_decision_audit")
    op.drop_index("ix_authorization_decision_audit_tenant_time", table_name="authorization_decision_audit")
    op.drop_table("authorization_decision_audit")
