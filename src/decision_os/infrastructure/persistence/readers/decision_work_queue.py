"""Database-bounded, tenant-scoped Decision Work Queue reader."""
import base64
import binascii
import json
from typing import Callable
from uuid import UUID

from sqlalchemy import and_, case as sql_case, exists, or_, select
from sqlalchemy.orm import Session

from decision_os.application.ports.decision_work_queue import (
    DecisionWorkQueueItem,
    DecisionWorkQueuePage,
    DecisionWorkQueueReader,
    InvalidQueueCursor,
)
from decision_os.domain.action import ActionStatus
from decision_os.domain.decision_case import CaseStatus
from decision_os.infrastructure.persistence.models.action import ActionModel
from decision_os.infrastructure.persistence.models.decision import DecisionModel
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel


_PRIORITY = {
    "REVIEW_CASE": 10,
    "MAKE_DECISION": 20,
    "APPROVE_DECISION": 30,
    "EXECUTE_ACTION": 40,
    "REVIEW_OUTCOME": 50,
}
_ATTENTION_STATES = frozenset(_PRIORITY)
_CASE_TYPES = frozenset({
    "PROJECT_MARGIN_RISK",
    "RESOURCE_CAPACITY_RISK",
    "REVENUE_BILLING_LEAKAGE",
})


def _encode_cursor(
    priority: int, case_id: UUID, *, attention_state: str | None, case_type: str | None,
) -> str:
    raw = json.dumps({
        "v": 1, "p": priority, "id": str(case_id),
        "a": attention_state, "c": case_type,
    }, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(
    value: str | None, *, attention_state: str | None, case_type: str | None,
) -> tuple[int, UUID] | None:
    if value is None:
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if (
            not isinstance(payload, dict)
            or set(payload) != {"v", "p", "id", "a", "c"}
            or type(payload["v"]) is not int
            or payload["v"] != 1
        ):
            raise ValueError
        priority = payload["p"]
        if isinstance(priority, bool) or priority not in _PRIORITY.values():
            raise ValueError
        case_id = UUID(payload["id"])
        if str(case_id) != payload["id"]:
            raise ValueError
        if payload["a"] != attention_state or payload["c"] != case_type:
            raise ValueError
        return priority, case_id
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as exc:
        raise InvalidQueueCursor("invalid queue cursor") from exc


class SQLAlchemyDecisionWorkQueueReader(DecisionWorkQueueReader):
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _attention(status: str, decision: DecisionModel | None, action: ActionModel | None = None) -> str:
        if status == CaseStatus.AWAITING_DECISION.value:
            return "MAKE_DECISION"
        if status == CaseStatus.AWAITING_APPROVAL.value:
            return "APPROVE_DECISION"
        if status == CaseStatus.APPROVED.value:
            return "EXECUTE_ACTION" if action is not None and action.status == ActionStatus.READY.value else "NO_ACTION"
        if status in {CaseStatus.OUTCOME_PENDING.value, CaseStatus.VERIFYING.value}:
            return "REVIEW_OUTCOME"
        if status in {CaseStatus.DETECTED.value, CaseStatus.TRIAGED.value, CaseStatus.ANALYZING.value, CaseStatus.OPTIONS_READY.value}:
            return "REVIEW_CASE"
        return "NO_ACTION"

    @staticmethod
    def _priority(attention: str) -> int:
        return _PRIORITY[attention]

    def list(
        self, *, tenant_id: UUID, limit: int = 50, cursor: str | None = None,
        attention_state: str | None = None, case_type: str | None = None,
    ) -> DecisionWorkQueuePage:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if attention_state is not None and attention_state not in _ATTENTION_STATES:
            raise ValueError("unknown attention state")
        if case_type is not None and case_type not in _CASE_TYPES:
            raise ValueError("unknown case type")
        decoded = _decode_cursor(cursor, attention_state=attention_state, case_type=case_type)

        ready_action = exists(
            select(ActionModel.id).where(
                ActionModel.case_id == DecisionCaseModel.id,
                ActionModel.tenant_id == DecisionCaseModel.tenant_id,
                ActionModel.status == ActionStatus.READY.value,
            )
        )
        attention_expr = sql_case(
            (DecisionCaseModel.status.in_([
                CaseStatus.DETECTED.value, CaseStatus.TRIAGED.value,
                CaseStatus.ANALYZING.value, CaseStatus.OPTIONS_READY.value,
            ]), "REVIEW_CASE"),
            (DecisionCaseModel.status == CaseStatus.AWAITING_DECISION.value, "MAKE_DECISION"),
            (DecisionCaseModel.status == CaseStatus.AWAITING_APPROVAL.value, "APPROVE_DECISION"),
            (and_(DecisionCaseModel.status == CaseStatus.APPROVED.value, ready_action), "EXECUTE_ACTION"),
            (DecisionCaseModel.status.in_([
                CaseStatus.OUTCOME_PENDING.value, CaseStatus.VERIFYING.value,
            ]), "REVIEW_OUTCOME"),
            else_="NO_ACTION",
        )
        priority_expr = sql_case(
            *[(attention_expr == state, priority) for state, priority in _PRIORITY.items()],
            else_=999,
        )
        stmt = (
            select(DecisionCaseModel, DecisionModel, attention_expr.label("attention"), priority_expr.label("priority"))
            .outerjoin(DecisionModel, DecisionModel.case_id == DecisionCaseModel.id)
            .where(DecisionCaseModel.tenant_id == tenant_id, attention_expr != "NO_ACTION")
        )
        if attention_state is not None:
            stmt = stmt.where(attention_expr == attention_state)
        if case_type is not None:
            stmt = stmt.where(DecisionCaseModel.case_type == case_type)
        if decoded is not None:
            last_priority, last_case_id = decoded
            stmt = stmt.where(or_(
                priority_expr > last_priority,
                and_(priority_expr == last_priority, DecisionCaseModel.id > last_case_id),
            ))
        stmt = stmt.order_by(priority_expr.asc(), DecisionCaseModel.id.asc()).limit(limit + 1)
        rows = self._session.execute(stmt).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = tuple(
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
            for case, decision, attention, _priority in rows
        )
        next_cursor = None
        if has_more and rows:
            _case, _decision, _attention, priority = rows[-1]
            next_cursor = _encode_cursor(priority, _case.id, attention_state=attention_state, case_type=case_type)
        return DecisionWorkQueuePage(items=items, next_cursor=next_cursor)


class SessionFactoryDecisionWorkQueueReader(DecisionWorkQueueReader):
    """Open and close a dedicated SQLAlchemy Session for each queue query."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def list(
        self, *, tenant_id: UUID, limit: int = 50, cursor: str | None = None,
        attention_state: str | None = None, case_type: str | None = None,
    ) -> DecisionWorkQueuePage:
        with self._session_factory() as session:
            return SQLAlchemyDecisionWorkQueueReader(session).list(
                tenant_id=tenant_id, limit=limit, cursor=cursor,
                attention_state=attention_state, case_type=case_type,
            )
