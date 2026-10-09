from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from decision_os.application.ports.decision_memory import DecisionMemoryView
from decision_os.infrastructure.persistence.models.decision_memory import DecisionMemoryProjectionModel


class SQLAlchemyDecisionMemoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, *, tenant_id: UUID, case_id: UUID) -> DecisionMemoryView | None:
        model = self._session.scalar(
            select(DecisionMemoryProjectionModel).where(
                DecisionMemoryProjectionModel.tenant_id == tenant_id,
                DecisionMemoryProjectionModel.case_id == case_id,
            )
        )
        if model is None:
            return None

        return DecisionMemoryView(
            tenant_id=model.tenant_id,
            case_id=model.case_id,
            case_type=model.case_type,
            case_title=model.case_title,
            case_status=model.case_status,
            decision_id=model.decision_id,
            decision_status=model.decision_status,
            rationale=model.rationale,
            decided_by=model.decided_by,
            selected_option_ids=tuple(UUID(value) for value in (model.selected_option_ids or [])),
            approval_required=model.approval_required,
            action_summary=model.action_summary,
            outcome_summary=model.outcome_summary,
            verification_summary=model.verification_summary,
            source_ids=model.source_ids or {},
            authoritative_version=model.authoritative_version,
            notified_version=model.notified_version,
            projected_version=model.projected_version,
            projected_at=model.projected_at,
            state=model.last_projection_state,
        )
