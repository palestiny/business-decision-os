"""add tenant and correlation metadata to outbox messages

Revision ID: 0007_outbox_operational_metadata
Revises: 0006_evidence_analysis
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_outbox_operational_metadata"
down_revision = "0006_evidence_analysis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outbox_messages", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("outbox_messages", sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_outbox_messages_tenant_id", "outbox_messages", ["tenant_id"])
    op.create_index("ix_outbox_messages_correlation_id", "outbox_messages", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_outbox_messages_correlation_id", table_name="outbox_messages")
    op.drop_index("ix_outbox_messages_tenant_id", table_name="outbox_messages")
    op.drop_column("outbox_messages", "correlation_id")
    op.drop_column("outbox_messages", "tenant_id")
