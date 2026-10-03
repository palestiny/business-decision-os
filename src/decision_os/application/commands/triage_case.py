from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.decision_case import DecisionCase, DomainError


@dataclass(frozen=True)
class TriageCaseCommand:
    tenant_id: UUID
    case_id: UUID
    actor_id: UUID


class TriageCaseHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: TriageCaseCommand) -> DecisionCase:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise DomainError("decision case not found")
        self._authorization.require(
            actor_id=command.actor_id,
            tenant_id=command.tenant_id,
            permission=Permission.TRIAGE_CASE,
            resource_id=command.case_id,
        )
        case.triage()
        self._uow.decision_cases.save(case)
        return case
