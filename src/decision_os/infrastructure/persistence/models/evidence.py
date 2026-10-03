from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from decision_os.infrastructure.persistence.base import Base


class EvidenceModel(Base):
    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    metric: Mapped[str] = mapped_column(String(160), nullable=False)
    value: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(80), nullable=False)
    period: Mapped[str] = mapped_column(String(80), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    snapshot: Mapped[str] = mapped_column(Text, nullable=False)


class AnalysisFindingModel(Base):
    __tablename__ = "analysis_findings"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    evidence_ids: Mapped[str] = mapped_column(Text, nullable=False)
