"""Decision case domain model.

Initial implementation intentionally keeps infrastructure out of the domain.
"""
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class CaseStatus(StrEnum):
    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    ANALYZING = "ANALYZING"
    OPTIONS_READY = "OPTIONS_READY"
    AWAITING_DECISION = "AWAITING_DECISION"
    DECISION_MADE = "DECISION_MADE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    OUTCOME_PENDING = "OUTCOME_PENDING"
    VERIFYING = "VERIFYING"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class DomainError(ValueError):
    """Base domain exception."""


class InvalidCaseTransition(DomainError):
    """Raised when a lifecycle transition is not allowed."""


@dataclass
class DecisionCase:
    id: UUID
    tenant_id: UUID
    case_type: str
    title: str
    status: CaseStatus = CaseStatus.DETECTED
    version: int = 0

    @classmethod
    def create(
        cls,
        *,
        id: UUID,
        tenant_id: UUID,
        case_type: str,
        title: str,
    ) -> "DecisionCase":
        if not case_type.strip():
            raise DomainError("case_type is required")
        if not title.strip():
            raise DomainError("title is required")
        return cls(
            id=id,
            tenant_id=tenant_id,
            case_type=case_type,
            title=title,
        )

    def triage(self) -> None:
        self._transition(CaseStatus.TRIAGED)

    def start_analysis(self) -> None:
        self._transition(CaseStatus.ANALYZING)

    def submit_options(self) -> None:
        self._transition(CaseStatus.OPTIONS_READY)

    def await_decision(self) -> None:
        self._transition(CaseStatus.AWAITING_DECISION)

    def record_decision(self, *, approval_required: bool) -> None:
        target = (
            CaseStatus.AWAITING_APPROVAL
            if approval_required
            else CaseStatus.APPROVED
        )
        self._transition(target)

    def approve(self) -> None:
        self._transition(CaseStatus.APPROVED)

    def reject(self) -> None:
        self._transition(CaseStatus.REJECTED)

    def _transition(self, target: CaseStatus) -> None:
        allowed = {
            CaseStatus.DETECTED: {CaseStatus.TRIAGED},
            CaseStatus.TRIAGED: {CaseStatus.ANALYZING},
            CaseStatus.ANALYZING: {CaseStatus.OPTIONS_READY},
            CaseStatus.OPTIONS_READY: {CaseStatus.AWAITING_DECISION},
            CaseStatus.AWAITING_DECISION: {
                CaseStatus.AWAITING_APPROVAL,
                CaseStatus.APPROVED,
            },
            CaseStatus.AWAITING_APPROVAL: {
                CaseStatus.APPROVED,
                CaseStatus.REJECTED,
            },
        }
        if target not in allowed.get(self.status, set()):
            raise InvalidCaseTransition(
                f"{self.status} -> {target} is not allowed"
            )
        self.status = target
        self.version += 1
