from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from decision_os.infrastructure.persistence.base import Base


class DecisionOptionModel(Base):
    __tablename__ = "decision_options"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)


class DecisionModel(Base):
    __tablename__ = "decisions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    authority_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approval_required: Mapped[bool] = mapped_column(nullable=False, default=False)

    __table_args__ = (UniqueConstraint("case_id", name="uq_decisions_case_id"),)


class DecisionSelectedOptionModel(Base):
    __tablename__ = "decision_selected_options"

    decision_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decisions.id", ondelete="CASCADE"), primary_key=True)
    option_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_options.id"), primary_key=True)
