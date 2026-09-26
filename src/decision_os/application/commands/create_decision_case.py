"""CreateDecisionCase application command."""
from dataclasses import dataclass
from uuid import UUID, uuid4

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.decision_case import DecisionCase


@dataclass(frozen=True)
class CreateDecisionCaseCommand:
    tenant_id: UUID
    case_type: str
    title: str
    actor_id: UUID
    case_id: UUID | None = None


class CreateDecisionCaseHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: CreateDecisionCaseCommand, *, commit: bool = True) -> DecisionCase:
        case_id = command.case_id or uuid4()
        self._authorization.require(
            actor_id=command.actor_id,
            tenant_id=command.tenant_id,
            permission=Permission.CREATE_CASE,
            resource_id=case_id,
        )
        case = DecisionCase.create(
            id=case_id,
            tenant_id=command.tenant_id,
            case_type=command.case_type,
            title=command.title,
        )
        self._uow.decision_cases.add(case)
        if commit:
            self._uow.commit()
        return case
