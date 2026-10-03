from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from decision_os.infrastructure.persistence.base import Base


class DecisionMemoryProjectionModel(Base):
    __tablename__ = "decision_memory_projections"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False, index=True)
    case_type: Mapped[str] = mapped_column(String(100), nullable=False)
    case_title: Mapped[str] = mapped_column(String(300), nullable=False)
    case_status: Mapped[str] = mapped_column(String(40), nullable=False)
    decision_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    decision_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    selected_option_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    approval_required: Mapped[bool | None] = mapped_column(nullable=True)
    action_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    outcome_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verification_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_ids: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    authoritative_version: Mapped[int] = mapped_column(Integer, nullable=False)
    notified_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    projected_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    projected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_projection_state: Mapped[str] = mapped_column(String(30), nullable=False, default="CURRENT")

    __table_args__ = (UniqueConstraint("tenant_id", "case_id", name="uq_decision_memory_tenant_case"),)
