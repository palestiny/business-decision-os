"""add authoritative decision memory projection

Revision ID: 0008_decision_memory_projection
Revises: 0007_outbox_operational_metadata
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_decision_memory_projection"
down_revision = "0007_outbox_operational_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_memory_projections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_type", sa.String(length=100), nullable=False),
        sa.Column("case_title", sa.String(length=300), nullable=False),
        sa.Column("case_status", sa.String(length=40), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision_status", sa.String(length=40), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("selected_option_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=True),
        sa.Column("action_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("outcome_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("verification_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("authoritative_version", sa.Integer(), nullable=False),
        sa.Column("projected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_projection_state", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["decision_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "case_id", name="uq_decision_memory_tenant_case"),
    )
    op.create_index("ix_decision_memory_projections_tenant_id", "decision_memory_projections", ["tenant_id"])
    op.create_index("ix_decision_memory_projections_case_id", "decision_memory_projections", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_decision_memory_projections_case_id", table_name="decision_memory_projections")
    op.drop_index("ix_decision_memory_projections_tenant_id", table_name="decision_memory_projections")
    op.drop_table("decision_memory_projections")
