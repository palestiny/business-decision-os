from dataclasses import dataclass
from uuid import UUID, uuid4

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.action import ActionExecution, ActionExecutionStatus, ActionStatus
from decision_os.domain.decision_case import CaseStatus


@dataclass(frozen=True)
class StartActionCommand:
    tenant_id: UUID
    action_id: UUID
    actor_id: UUID
    execution_id: UUID | None = None


class StartActionHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: StartActionCommand) -> ActionExecution:
        action = self._uow.actions.get(command.action_id, command.tenant_id)
        if action is None:
            raise ValueError("action not found")
        self._authorization.require(
            actor_id=command.actor_id, tenant_id=command.tenant_id,
            permission=Permission.START_ACTION, resource_id=action.case_id,
        )
        if action.status is not ActionStatus.READY:
            raise ValueError("action must be ready before execution")
        case = self._uow.decision_cases.get(action.case_id, command.tenant_id)
        if case is None:
            raise ValueError("decision case not found")
        if case.status is not CaseStatus.APPROVED:
            raise ValueError("decision case must be approved before execution")
        latest = self._uow.action_executions.get_latest_for_action(action.id)
        if latest is not None and latest.status is ActionExecutionStatus.UNKNOWN:
            raise ValueError("action execution outcome is unknown; reconciliation is required before retry")
        expected_version = action.version
        attempt = 1 if latest is None else latest.attempt + 1
        execution = ActionExecution.request(
            id=command.execution_id or uuid4(), action_id=action.id, attempt=attempt,
        )
        action.start_execution()
        self._uow.actions.save(action, expected_version=expected_version)
        case.execute()
        self._uow.decision_cases.save(case)
        self._uow.action_executions.add(execution)
        return execution
