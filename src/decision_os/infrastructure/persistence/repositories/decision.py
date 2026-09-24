from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from decision_os.domain.decision import Decision, DecisionStatus
from decision_os.infrastructure.persistence.models.decision import (
    DecisionModel,
    DecisionSelectedOptionModel,
)
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel


class SQLAlchemyDecisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, decision_id: UUID, tenant_id: UUID) -> Decision | None:
        row = self._session.execute(
            select(DecisionModel, DecisionCaseModel)
            .join(DecisionCaseModel, DecisionCaseModel.id == DecisionModel.case_id)
            .where(DecisionModel.id == decision_id, DecisionCaseModel.tenant_id == tenant_id)
        ).one_or_none()
        if row is None:
            return None
        model, _case = row
        option_ids = tuple(
            self._session.scalars(
                select(DecisionSelectedOptionModel.option_id).where(
                    DecisionSelectedOptionModel.decision_id == model.id
                )
            ).all()
        )
        return Decision(
            id=model.id,
            case_id=model.case_id,
            selected_option_ids=option_ids,
            rationale=model.rationale,
            status=DecisionStatus(model.status),
            decided_by=model.decided_by,
            _approval_required=model.approval_required,
        )

    def add(self, decision: Decision) -> None:
        now = datetime.now(timezone.utc)
        self._session.add(DecisionModel(
            id=decision.id,
            case_id=decision.case_id,
            status=decision.status.value,
            rationale=decision.rationale,
            decided_by=decision.decided_by,
            decided_at=now,
            created_at=now,
            approval_required=decision._approval_required,
        ))
        self._session.add_all(
            DecisionSelectedOptionModel(decision_id=decision.id, option_id=option_id)
            for option_id in decision.selected_option_ids
        )

    def save(self, decision: Decision) -> None:
        model = self._session.get(DecisionModel, decision.id)
        if model is None:
            raise ValueError("decision not found")
        model.status = decision.status.value
