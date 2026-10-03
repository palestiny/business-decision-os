"""Authority and policy boundaries."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class Permission(StrEnum):
    CREATE_CASE = "CREATE_CASE"
    TRIAGE_CASE = "TRIAGE_CASE"
    START_ANALYSIS = "START_ANALYSIS"
    SUBMIT_OPTIONS = "SUBMIT_OPTIONS"
    AWAIT_DECISION = "AWAIT_DECISION"
    MAKE_DECISION = "MAKE_DECISION"
    APPROVE_DECISION = "APPROVE_DECISION"
    REJECT_DECISION = "REJECT_DECISION"
    CREATE_ACTION = "CREATE_ACTION"
    START_ACTION = "START_ACTION"
    UPDATE_EXECUTION = "UPDATE_EXECUTION"
    RECONCILE_EXECUTION = "RECONCILE_EXECUTION"
    CREATE_OUTCOME = "CREATE_OUTCOME"
    VERIFY_OUTCOME = "VERIFY_OUTCOME"
    CREATE_EVIDENCE = "CREATE_EVIDENCE"
    ADD_ANALYSIS = "ADD_ANALYSIS"


class AuthorizationDenied(PermissionError):
    """Raised when the actor lacks required authority."""


class PolicyEvaluationUnavailable(RuntimeError):
    """Raised when approval policy evaluation cannot produce a trustworthy result."""


@dataclass(frozen=True)
class ApprovalDecision:
    required: bool
    policy_ids: tuple[UUID, ...] = ()


class AuthorizationPort(Protocol):
    def require(self, *, actor_id: UUID, tenant_id: UUID, permission: Permission, resource_id: UUID) -> None:
        ...


class PolicyEvaluatorPort(Protocol):
    def evaluate(self, *, actor_id: UUID, tenant_id: UUID, case_id: UUID) -> ApprovalDecision:
        ...
