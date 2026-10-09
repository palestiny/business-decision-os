from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.decision_case import DecisionCase


@dataclass(frozen=True)
class AwaitDecisionCommand:
    tenant_id: UUID
    case_id: UUID
    actor_id: UUID
    correlation_id: UUID | None = None

class AwaitDecisionHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: AwaitDecisionCommand) -> DecisionCase:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise ValueError("decision case not found")
        self._authorization.require(
            actor_id=command.actor_id,
            tenant_id=command.tenant_id,
            permission=Permission.AWAIT_DECISION,
            resource_id=command.case_id,, correlation_id=command.correlation_id)
        options = self._uow.decision_options.list_for_case(case_id=case.id, tenant_id=case.tenant_id)
        if not options:
            raise ValueError("decision options are required before awaiting decision")
        case.await_decision()
        self._uow.decision_cases.save(case)
        return case
