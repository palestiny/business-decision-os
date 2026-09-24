"""CreateDecisionCase application command."""
from dataclasses import dataclass
from uuid import UUID, uuid4

from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.decision_case import DecisionCase


@dataclass(frozen=True)
class CreateDecisionCaseCommand:
    tenant_id: UUID
    case_type: str
    title: str
    case_id: UUID | None = None


class CreateDecisionCaseHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def handle(self, command: CreateDecisionCaseCommand) -> DecisionCase:
        case = DecisionCase.create(
            id=command.case_id or uuid4(),
            tenant_id=command.tenant_id,
            case_type=command.case_type,
            title=command.title,
        )
        self._uow.decision_cases.add(case)
        self._uow.commit()
        return case
