from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.outcome import ActualOutcome, InvalidOutcome


@dataclass(frozen=True)
class RecordActualOutcomeCommand:
    tenant_id: UUID
    case_id: UUID
    actor_id: UUID
    outcome_id: UUID
    expected_outcome_id: UUID
    observed_value: float
    correlation_id: UUID | None = None

class RecordActualOutcomeHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: RecordActualOutcomeCommand) -> ActualOutcome:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise InvalidOutcome("decision case not found")
        expected = self._uow.expected_outcomes.get(command.expected_outcome_id, command.tenant_id)
        if expected is None or expected.case_id != case.id:
            raise InvalidOutcome("expected outcome not found")
        self._authorization.require(actor_id=command.actor_id, tenant_id=command.tenant_id, permission=Permission.CREATE_OUTCOME, resource_id=case.id, correlation_id=command.correlation_id)
        outcome = ActualOutcome(id=command.outcome_id, case_id=case.id, expected_outcome_id=expected.id, observed_value=command.observed_value)
        self._uow.actual_outcomes.add(outcome, command.tenant_id)
        return outcome
