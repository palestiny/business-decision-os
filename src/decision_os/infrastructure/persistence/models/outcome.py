from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from decision_os.infrastructure.persistence.base import Base


class ExpectedOutcomeModel(Base):
    __tablename__ = "expected_outcomes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(160), nullable=False)
    operator: Mapped[str] = mapped_column(String(10), nullable=False)
    target: Mapped[str] = mapped_column(String(80), nullable=False)


class ActualOutcomeModel(Base):
    __tablename__ = "actual_outcomes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False, index=True)
    expected_outcome_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("expected_outcomes.id"), nullable=False, index=True)
    observed_value: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class VerificationModel(Base):
    __tablename__ = "verifications"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False, index=True)
    actual_outcome_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("actual_outcomes.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
