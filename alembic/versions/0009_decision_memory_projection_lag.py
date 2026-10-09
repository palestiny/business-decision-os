"""add explicit decision memory projection lag metadata

Revision ID: 0009_decision_memory_lag
Revises: 0008_decision_memory_projection
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_decision_memory_lag"
down_revision = "0008_decision_memory_projection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("decision_memory_projections", sa.Column("notified_version", sa.Integer(), nullable=True))
    op.add_column("decision_memory_projections", sa.Column("projected_version", sa.Integer(), nullable=True))
    op.create_index(
        "ix_decision_memory_projections_state",
        "decision_memory_projections",
        ["last_projection_state"],
    )


def downgrade() -> None:
    op.drop_index("ix_decision_memory_projections_state", table_name="decision_memory_projections")
    op.drop_column("decision_memory_projections", "projected_version")
    op.drop_column("decision_memory_projections", "notified_version")
