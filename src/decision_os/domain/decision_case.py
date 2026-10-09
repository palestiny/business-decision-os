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


class DomainError(ValueError): ...
class InvalidCaseTransition(DomainError): ...


@dataclass
class DecisionCase:
    id: UUID
    tenant_id: UUID
    case_type: str
    title: str
    status: CaseStatus = CaseStatus.DETECTED
    version: int = 0
    created_by: UUID | None = None

    @classmethod
    def create(cls, *, id: UUID, tenant_id: UUID, case_type: str, title: str, created_by: UUID | None = None) -> "DecisionCase":
        if not case_type.strip(): raise DomainError("case_type is required")
        if not title.strip(): raise DomainError("title is required")
        return cls(id=id, tenant_id=tenant_id, case_type=case_type, title=title, created_by=created_by)

    def triage(self) -> None: self._transition(CaseStatus.TRIAGED)
    def start_analysis(self) -> None: self._transition(CaseStatus.ANALYZING)
    def submit_options(self) -> None: self._transition(CaseStatus.OPTIONS_READY)
    def await_decision(self) -> None: self._transition(CaseStatus.AWAITING_DECISION)

    def record_decision(self, *, approval_required: bool) -> None:
        self._transition(CaseStatus.DECISION_MADE)
        if approval_required: self._transition(CaseStatus.AWAITING_APPROVAL)
        else: self._transition(CaseStatus.APPROVED)

    def approve(self) -> None: self._transition(CaseStatus.APPROVED)
    def reject(self) -> None: self._transition(CaseStatus.REJECTED)
    def execute(self) -> None: self._transition(CaseStatus.EXECUTING)
    def outcome_pending(self) -> None: self._transition(CaseStatus.OUTCOME_PENDING)
    def start_verification(self) -> None: self._transition(CaseStatus.VERIFYING)
    def close(self) -> None: self._transition(CaseStatus.CLOSED)

    def _transition(self, target: CaseStatus) -> None:
        allowed = {
            CaseStatus.DETECTED: {CaseStatus.TRIAGED},
            CaseStatus.TRIAGED: {CaseStatus.ANALYZING},
            CaseStatus.ANALYZING: {CaseStatus.OPTIONS_READY},
            CaseStatus.OPTIONS_READY: {CaseStatus.AWAITING_DECISION},
            CaseStatus.AWAITING_DECISION: {CaseStatus.DECISION_MADE},
            CaseStatus.DECISION_MADE: {CaseStatus.AWAITING_APPROVAL, CaseStatus.APPROVED},
            CaseStatus.AWAITING_APPROVAL: {CaseStatus.APPROVED, CaseStatus.REJECTED},
            CaseStatus.APPROVED: {CaseStatus.EXECUTING},
            CaseStatus.EXECUTING: {CaseStatus.OUTCOME_PENDING},
            CaseStatus.OUTCOME_PENDING: {CaseStatus.VERIFYING},
            CaseStatus.VERIFYING: {CaseStatus.CLOSED},
        }
        if target not in allowed.get(self.status, set()):
            raise InvalidCaseTransition(f"{self.status} -> {target} is not allowed")
        self.status = target
        self.version += 1
