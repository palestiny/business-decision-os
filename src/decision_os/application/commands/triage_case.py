from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.decision_case import DecisionCase, DomainError


@dataclass(frozen=True)
class TriageCaseCommand:
    tenant_id: UUID
    case_id: UUID


class TriageCaseHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def handle(self, command: TriageCaseCommand) -> DecisionCase:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise DomainError("decision case not found")
        case.triage()
        self._uow.decision_cases.save(case)
        self._uow.commit()
        return case
