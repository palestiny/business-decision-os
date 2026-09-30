from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.action import ActionExecutionStatus, ActionStatus, InvalidAction


@dataclass(frozen=True)
class CompleteActionExecutionCommand:
    tenant_id: UUID
    execution_id: UUID
    actor_id: UUID
    outcome: ActionExecutionStatus


class CompleteActionExecutionHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: CompleteActionExecutionCommand):
        if command.outcome not in {ActionExecutionStatus.SUCCEEDED, ActionExecutionStatus.FAILED}:
            raise InvalidAction("completion requires a known terminal outcome")
        execution = self._uow.action_executions.get(command.execution_id)
        if execution is None:
            raise InvalidAction("execution not found")
        action = self._uow.actions.get(execution.action_id, command.tenant_id)
        if action is None:
            raise InvalidAction("action not found")
        self._authorization.require(actor_id=command.actor_id, tenant_id=command.tenant_id, permission=Permission.UPDATE_EXECUTION, resource_id=action.case_id)
        if action.status is not ActionStatus.EXECUTING:
            raise InvalidAction("action must be executing")
        expected_action_version = action.version
        if command.outcome is ActionExecutionStatus.SUCCEEDED:
            execution.succeed()
            action.complete()
        else:
            execution.fail()
            action.fail()
        self._uow.action_executions.save(execution)
        self._uow.actions.save(action, expected_version=expected_action_version)
        case = self._uow.decision_cases.get(action.case_id, command.tenant_id)
        if case is None:
            raise InvalidAction("decision case not found")
        expected_case_version = case.version
        case.outcome_pending()
        self._uow.decision_cases.save(case, expected_version=expected_case_version)
        return execution
