"""add server-managed external identity mappings

Revision ID: 0010_external_identity_mappings
Revises: 0009_decision_memory_lag
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_external_identity_mappings"
down_revision = "0009_decision_memory_lag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_identity_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("issuer", sa.String(500), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("tenant_key", sa.String(255), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("issuer", "subject", "tenant_key", name="uq_external_identity_mapping_key"),
    )
    op.create_index("ix_external_identity_mappings_tenant_id", "external_identity_mappings", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_external_identity_mappings_tenant_id", table_name="external_identity_mappings")
    op.drop_table("external_identity_mappings")
