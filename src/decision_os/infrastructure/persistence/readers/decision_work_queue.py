from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from decision_os.application.ports.decision_work_queue import (
    DecisionWorkQueueItem,
    DecisionWorkQueueReader,
)
from decision_os.domain.decision_case import CaseStatus
from decision_os.infrastructure.persistence.models.decision import DecisionModel
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel


class SQLAlchemyDecisionWorkQueueReader(DecisionWorkQueueReader):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, *, tenant_id: UUID) -> tuple[DecisionWorkQueueItem, ...]:
        rows = self._session.execute(
            select(DecisionCaseModel, DecisionModel)
            .outerjoin(DecisionModel, DecisionModel.case_id == DecisionCaseModel.id)
            .where(DecisionCaseModel.tenant_id == tenant_id)
        ).all()

        items = []
        for case, decision in rows:
            attention = self._attention(case.status, decision)
            if attention == "NO_ACTION":
                continue
            items.append(
                DecisionWorkQueueItem(
                    tenant_id=case.tenant_id,
                    case_id=case.id,
                    case_type=case.case_type,
                    title=case.title,
                    case_status=case.status,
                    attention_state=attention,
                    decision_id=decision.id if decision else None,
                    decision_status=decision.status if decision else None,
                    approval_required=decision.approval_required if decision else None,
                    authoritative_version=case.version,
                    projection_state=None,
                )
            )

        return tuple(sorted(items, key=lambda item: (self._priority(item.attention_state), str(item.case_id))))

    @staticmethod
    def _attention(status: str, decision: DecisionModel | None) -> str:
        if status == CaseStatus.AWAITING_DECISION.value:
            return "MAKE_DECISION"
        if status == CaseStatus.AWAITING_APPROVAL.value:
            return "APPROVE_DECISION"
        if status == CaseStatus.APPROVED.value:
            return "EXECUTE_ACTION"
        if status in {CaseStatus.OUTCOME_PENDING.value, CaseStatus.VERIFYING.value}:
            return "REVIEW_OUTCOME"
        if status in {CaseStatus.DETECTED.value, CaseStatus.TRIAGED.value, CaseStatus.ANALYZING.value, CaseStatus.OPTIONS_READY.value}:
            return "REVIEW_CASE"
        return "NO_ACTION"

    @staticmethod
    def _priority(attention: str) -> int:
        return {
            "REVIEW_CASE": 10,
            "MAKE_DECISION": 20,
            "APPROVE_DECISION": 30,
            "EXECUTE_ACTION": 40,
            "REVIEW_OUTCOME": 50,
        }[attention]
