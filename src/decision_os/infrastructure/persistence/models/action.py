from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from decision_os.infrastructure.persistence.base import Base


class ActionModel(Base):
    __tablename__ = "actions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False, index=True)
    decision_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decisions.id"), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(120), nullable=False)
    parameters: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ActionExecutionModel(Base):
    __tablename__ = "action_executions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    action_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)

    __table_args__ = (
        UniqueConstraint("action_id", "attempt", name="uq_action_executions_action_attempt"),
    )
