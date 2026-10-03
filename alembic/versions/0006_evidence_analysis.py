"""create evidence and analysis finding tables

Revision ID: 0006_evidence_analysis
Revises: 0005_business_outcomes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_evidence_analysis"
down_revision = "0005_business_outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decision_cases.id"), nullable=False),
        sa.Column("source", sa.String(160), nullable=False),
        sa.Column("metric", sa.String(160), nullable=False),
        sa.Column("value", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(80), nullable=False),
        sa.Column("period", sa.String(80), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=False),
    )
    op.create_index("ix_evidence_tenant_id", "evidence", ["tenant_id"])
    op.create_index("ix_evidence_case_id", "evidence", ["case_id"])

    op.create_table(
        "analysis_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decision_cases.id"), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_ids", sa.Text(), nullable=False),
    )
    op.create_index("ix_analysis_findings_tenant_id", "analysis_findings", ["tenant_id"])
    op.create_index("ix_analysis_findings_case_id", "analysis_findings", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_findings_case_id", table_name="analysis_findings")
    op.drop_index("ix_analysis_findings_tenant_id", table_name="analysis_findings")
    op.drop_table("analysis_findings")
    op.drop_index("ix_evidence_case_id", table_name="evidence")
    op.drop_index("ix_evidence_tenant_id", table_name="evidence")
    op.drop_table("evidence")
