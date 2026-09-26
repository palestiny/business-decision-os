"""create decision core tables

Revision ID: 0002_decision_core
Revises: 0001_initial_platform
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_decision_core"
down_revision = "0001_initial_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_decision_cases_tenant_id", "decision_cases", ["tenant_id"])

    op.create_table(
        "decision_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decision_cases.id"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
    )
    op.create_index("ix_decision_options_case_id", "decision_options", ["case_id"])

    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decision_cases.id"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authority_snapshot", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("case_id", name="uq_decisions_case_id"),
    )
    op.create_index("ix_decisions_case_id", "decisions", ["case_id"])

    op.create_table(
        "decision_selected_options",
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decisions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("option_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decision_options.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("decision_selected_options")
    op.drop_index("ix_decisions_case_id", table_name="decisions")
    op.drop_table("decisions")
    op.drop_index("ix_decision_options_case_id", table_name="decision_options")
    op.drop_table("decision_options")
    op.drop_index("ix_decision_cases_tenant_id", table_name="decision_cases")
    op.drop_table("decision_cases")
