"""Durable, append-only-by-application authorization decision audit."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from decision_os.infrastructure.persistence.base import Base


class AuthorizationDecisionAuditModel(Base):
    __tablename__ = "authorization_decision_audit"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    permission: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    outcome: Mapped[str] = mapped_column(String(8), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    __table_args__ = (
        CheckConstraint("outcome IN ('ALLOW', 'DENY')", name="ck_authorization_decision_audit_outcome"),
        Index("ix_authorization_decision_audit_tenant_time", "tenant_id", "occurred_at"),
        Index("ix_authorization_decision_audit_actor_time", "actor_id", "occurred_at"),
        Index("ix_authorization_decision_audit_resource", "resource_id"),
        Index("ix_authorization_decision_audit_correlation_id", "correlation_id"),
    )
