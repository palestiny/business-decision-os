"""create action and action execution tables

Revision ID: 0004_action_execution
Revises: 0003_reliability
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_action_execution"
down_revision = "0003_reliability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decision_cases.id"), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decisions.id"), nullable=False),
        sa.Column("action_type", sa.String(120), nullable=False),
        sa.Column("parameters", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_actions_tenant_id", "actions", ["tenant_id"])
    op.create_index("ix_actions_case_id", "actions", ["case_id"])
    op.create_index("ix_actions_decision_id", "actions", ["decision_id"])

    op.create_table(
        "action_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("actions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.UniqueConstraint("action_id", "attempt", name="uq_action_executions_action_attempt"),
    )
    op.create_index("ix_action_executions_action_id", "action_executions", ["action_id"])


def downgrade() -> None:
    op.drop_index("ix_action_executions_action_id", table_name="action_executions")
    op.drop_table("action_executions")
    op.drop_index("ix_actions_decision_id", table_name="actions")
    op.drop_index("ix_actions_case_id", table_name="actions")
    op.drop_index("ix_actions_tenant_id", table_name="actions")
    op.drop_table("actions")
