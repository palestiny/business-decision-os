from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.action import ActionExecutionStatus, ActionStatus, InvalidAction


@dataclass(frozen=True)
class MarkExecutionUnknownCommand:
    tenant_id: UUID
    execution_id: UUID
    actor_id: UUID
    correlation_id: UUID | None = None

class MarkExecutionUnknownHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: MarkExecutionUnknownCommand):
        execution = self._uow.action_executions.get(command.execution_id)
        if execution is None:
            raise InvalidAction("execution not found")
        action = self._uow.actions.get(execution.action_id, command.tenant_id)
        if action is None:
            raise InvalidAction("action not found")
        self._authorization.require(actor_id=command.actor_id, tenant_id=command.tenant_id, permission=Permission.UPDATE_EXECUTION, resource_id=action.case_id, correlation_id=command.correlation_id)
        if action.status is not ActionStatus.EXECUTING:
            raise InvalidAction("action must be executing")
        expected_execution_status = execution.status
        execution.mark_unknown()
        self._uow.action_executions.save(execution, expected_status=expected_execution_status)
        return execution
