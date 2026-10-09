"""persist decision-case creator and approval attribution

Revision ID: 0013_separation_of_duties
Revises: 0012_authorization_admin_audit
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_separation_of_duties"
down_revision = "0012_authorization_admin_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "decision_cases",
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_decision_cases_created_by", "decision_cases", ["created_by"])
    op.add_column(
        "decisions",
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "decisions",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_decisions_approved_by", "decisions", ["approved_by"])


def downgrade() -> None:
    op.drop_index("ix_decisions_approved_by", table_name="decisions")
    op.drop_column("decisions", "approved_at")
    op.drop_column("decisions", "approved_by")
    op.drop_index("ix_decision_cases_created_by", table_name="decision_cases")
    op.drop_column("decision_cases", "created_by")
