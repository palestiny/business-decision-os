from typing import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from decision_os.application.ports.decision_work_queue import (
    DecisionWorkQueueItem,
    DecisionWorkQueueReader,
)
from decision_os.domain.action import ActionStatus
from decision_os.domain.decision_case import CaseStatus
from decision_os.infrastructure.persistence.models.action import ActionModel
from decision_os.infrastructure.persistence.models.decision import DecisionModel
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel


class SQLAlchemyDecisionWorkQueueReader(DecisionWorkQueueReader):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, *, tenant_id: UUID) -> tuple[DecisionWorkQueueItem, ...]:
        rows = self._session.execute(
            select(DecisionCaseModel, DecisionModel, ActionModel)
            .outerjoin(DecisionModel, DecisionModel.case_id == DecisionCaseModel.id)
            .outerjoin(
                ActionModel,
                (ActionModel.case_id == DecisionCaseModel.id)
                & (ActionModel.tenant_id == DecisionCaseModel.tenant_id),
            )
            .where(DecisionCaseModel.tenant_id == tenant_id)
        ).all()

        by_case = {}
        for case, decision, action in rows:
            current = by_case.get(case.id)
            if current is None:
                by_case[case.id] = (case, decision, action)
            elif action is not None and action.status == ActionStatus.READY.value:
                by_case[case.id] = (case, decision, action)

        items = []
        for case, decision, action in by_case.values():
            attention = self._attention(case.status, decision, action)
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
    def _attention(status: str, decision: DecisionModel | None, action: ActionModel | None = None) -> str:
        if status == CaseStatus.AWAITING_DECISION.value:
            return "MAKE_DECISION"
        if status == CaseStatus.AWAITING_APPROVAL.value:
            return "APPROVE_DECISION"
        if status == CaseStatus.APPROVED.value:
            if action is not None and action.status == ActionStatus.READY.value:
                return "EXECUTE_ACTION"
            return "NO_ACTION"
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



class SessionFactoryDecisionWorkQueueReader(DecisionWorkQueueReader):
    """Open and close a dedicated SQLAlchemy Session for each queue query."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def list(self, *, tenant_id: UUID) -> tuple[DecisionWorkQueueItem, ...]:
        with self._session_factory() as session:
            return SQLAlchemyDecisionWorkQueueReader(session).list(tenant_id=tenant_id)
