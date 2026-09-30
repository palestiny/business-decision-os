from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.outcome import ExpectedOutcome, InvalidOutcome


@dataclass(frozen=True)
class CreateExpectedOutcomeCommand:
    tenant_id: UUID
    case_id: UUID
    actor_id: UUID
    outcome_id: UUID
    metric: str
    operator: str
    target: float


class CreateExpectedOutcomeHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: CreateExpectedOutcomeCommand) -> ExpectedOutcome:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise InvalidOutcome("decision case not found")
        self._authorization.require(actor_id=command.actor_id, tenant_id=command.tenant_id, permission=Permission.CREATE_OUTCOME, resource_id=case.id)
        outcome = ExpectedOutcome.create(id=command.outcome_id, case_id=case.id, metric=command.metric, operator=command.operator, target=command.target)
        self._uow.expected_outcomes.add(outcome, command.tenant_id)
        return outcome
