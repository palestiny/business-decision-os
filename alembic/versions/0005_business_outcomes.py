"""create business outcome and verification tables

Revision ID: 0005_business_outcomes
Revises: 0004_action_execution
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_business_outcomes"
down_revision = "0004_action_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "expected_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decision_cases.id"), nullable=False),
        sa.Column("metric", sa.String(160), nullable=False),
        sa.Column("operator", sa.String(10), nullable=False),
        sa.Column("target", sa.String(80), nullable=False),
    )
    op.create_index("ix_expected_outcomes_tenant_id", "expected_outcomes", ["tenant_id"])
    op.create_index("ix_expected_outcomes_case_id", "expected_outcomes", ["case_id"])

    op.create_table(
        "actual_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decision_cases.id"), nullable=False),
        sa.Column("expected_outcome_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("expected_outcomes.id"), nullable=False),
        sa.Column("observed_value", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
    )
    op.create_index("ix_actual_outcomes_tenant_id", "actual_outcomes", ["tenant_id"])
    op.create_index("ix_actual_outcomes_case_id", "actual_outcomes", ["case_id"])
    op.create_index("ix_actual_outcomes_expected_outcome_id", "actual_outcomes", ["expected_outcome_id"])

    op.create_table(
        "verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decision_cases.id"), nullable=False),
        sa.Column("actual_outcome_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("actual_outcomes.id"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
    )
    op.create_index("ix_verifications_tenant_id", "verifications", ["tenant_id"])
    op.create_index("ix_verifications_case_id", "verifications", ["case_id"])
    op.create_index("ix_verifications_actual_outcome_id", "verifications", ["actual_outcome_id"])


def downgrade() -> None:
    op.drop_index("ix_verifications_actual_outcome_id", table_name="verifications")
    op.drop_index("ix_verifications_case_id", table_name="verifications")
    op.drop_index("ix_verifications_tenant_id", table_name="verifications")
    op.drop_table("verifications")
    op.drop_index("ix_actual_outcomes_expected_outcome_id", table_name="actual_outcomes")
    op.drop_index("ix_actual_outcomes_case_id", table_name="actual_outcomes")
    op.drop_index("ix_actual_outcomes_tenant_id", table_name="actual_outcomes")
    op.drop_table("actual_outcomes")
    op.drop_index("ix_expected_outcomes_case_id", table_name="expected_outcomes")
    op.drop_index("ix_expected_outcomes_tenant_id", table_name="expected_outcomes")
    op.drop_table("expected_outcomes")
