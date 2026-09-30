from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.action import ActionExecutionStatus, InvalidAction


@dataclass(frozen=True)
class ReconcileUnknownExecutionCommand:
    tenant_id: UUID
    execution_id: UUID
    actor_id: UUID
    observed_outcome: ActionExecutionStatus


class ReconcileUnknownExecutionHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: ReconcileUnknownExecutionCommand):
        if command.observed_outcome not in {ActionExecutionStatus.SUCCEEDED, ActionExecutionStatus.FAILED}:
            raise InvalidAction("reconciliation requires a known terminal outcome")
        execution = self._uow.action_executions.get(command.execution_id)
        if execution is None:
            raise InvalidAction("execution not found")
        action = self._uow.actions.get_by_id_for_tenant(execution.action_id, command.tenant_id)
        if action is None:
            raise InvalidAction("action not found")
        self._authorization.require(actor_id=command.actor_id, tenant_id=command.tenant_id, permission=Permission.RECONCILE_EXECUTION, resource_id=action.case_id)
        if execution.status.name != "UNKNOWN":
            raise InvalidAction("only unknown executions can be reconciled")
        if action.status.name != "EXECUTING":
            raise InvalidAction("action must remain executing during reconciliation")
        execution.reconcile(observed_status=command.observed_outcome)
        if command.observed_outcome is ActionExecutionStatus.SUCCEEDED:
            action.complete()
        else:
            action.fail()
        self._uow.action_executions.save(execution)
        expected_version = action.version - 1
        self._uow.actions.save(action, expected_version=expected_version)
        case = self._uow.decision_cases.get(action.case_id, command.tenant_id)
        if case is None:
            raise InvalidAction("decision case not found")
        expected_case_version = case.version
        case.outcome_pending()
        self._uow.decision_cases.save(case, expected_version=expected_case_version)
        return execution
