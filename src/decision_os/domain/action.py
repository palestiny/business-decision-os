"""Action and execution domain primitives."""
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ActionStatus(StrEnum):
    PLANNED = "PLANNED"
    READY = "READY"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class ActionExecutionStatus(StrEnum):
    REQUESTED = "REQUESTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class InvalidAction(ValueError):
    """Raised when an action violates a domain invariant."""


@dataclass
class Action:
    id: UUID
    tenant_id: UUID
    case_id: UUID
    decision_id: UUID
    action_type: str
    parameters: str
    status: ActionStatus = ActionStatus.PLANNED
    version: int = 0

    @classmethod
    def create(cls, *, id: UUID, tenant_id: UUID, case_id: UUID, decision_id: UUID, action_type: str, parameters: str) -> "Action":
        if not action_type.strip():
            raise InvalidAction("action_type is required")
        return cls(id=id, tenant_id=tenant_id, case_id=case_id, decision_id=decision_id, action_type=action_type.strip(), parameters=parameters)

    def ready(self) -> None:
        if self.status is not ActionStatus.PLANNED:
            raise InvalidAction("only planned actions can become ready")
        self.status = ActionStatus.READY
        self.version += 1

    def start_execution(self) -> None:
        if self.status is not ActionStatus.READY:
            raise InvalidAction("only ready actions can start execution")
        self.status = ActionStatus.EXECUTING
        self.version += 1

    def complete(self) -> None:
        if self.status is not ActionStatus.EXECUTING:
            raise InvalidAction("only executing actions can complete")
        self.status = ActionStatus.COMPLETED
        self.version += 1

    def fail(self) -> None:
        if self.status is not ActionStatus.EXECUTING:
            raise InvalidAction("only executing actions can fail")
        self.status = ActionStatus.FAILED
        self.version += 1


@dataclass
class ActionExecution:
    id: UUID
    action_id: UUID
    attempt: int
    status: ActionExecutionStatus = ActionExecutionStatus.REQUESTED

    @classmethod
    def request(cls, *, id: UUID, action_id: UUID, attempt: int) -> "ActionExecution":
        if attempt < 1:
            raise InvalidAction("execution attempt must be positive")
        return cls(id=id, action_id=action_id, attempt=attempt)

    def start(self) -> None:
        if self.status is not ActionExecutionStatus.REQUESTED:
            raise InvalidAction("only requested executions can start")
        self.status = ActionExecutionStatus.RUNNING

    def succeed(self) -> None:
        if self.status is not ActionExecutionStatus.RUNNING:
            raise InvalidAction("only running executions can succeed")
        self.status = ActionExecutionStatus.SUCCEEDED

    def fail(self) -> None:
        if self.status is not ActionExecutionStatus.RUNNING:
            raise InvalidAction("only running executions can fail")
        self.status = ActionExecutionStatus.FAILED

    def mark_unknown(self) -> None:
        if self.status is not ActionExecutionStatus.RUNNING:
            raise InvalidAction("only running executions can become unknown")
        self.status = ActionExecutionStatus.UNKNOWN

    def reconcile(self, *, observed_status: ActionExecutionStatus) -> None:
        if self.status is not ActionExecutionStatus.UNKNOWN:
            raise InvalidAction("only unknown executions can be reconciled")
        if observed_status not in {ActionExecutionStatus.SUCCEEDED, ActionExecutionStatus.FAILED}:
            raise InvalidAction("reconciliation requires a known terminal outcome")
        self.status = observed_status
