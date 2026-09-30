from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.outcome import InvalidOutcome, Verification


@dataclass(frozen=True)
class VerifyOutcomeCommand:
    tenant_id: UUID
    case_id: UUID
    actor_id: UUID
    verification_id: UUID
    actual_outcome_id: UUID


class VerifyOutcomeHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: VerifyOutcomeCommand) -> Verification:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise InvalidOutcome("decision case not found")
        actual = self._uow.actual_outcomes.get(command.actual_outcome_id, command.tenant_id)
        if actual is None or actual.case_id != case.id:
            raise InvalidOutcome("actual outcome not found")
        expected = self._uow.expected_outcomes.get(actual.expected_outcome_id, command.tenant_id)
        if expected is None:
            raise InvalidOutcome("expected outcome not found")
        self._authorization.require(actor_id=command.actor_id, tenant_id=command.tenant_id, permission=Permission.UPDATE_EXECUTION, resource_id=case.id)
        verification = Verification(id=command.verification_id, case_id=case.id, actual_outcome_id=actual.id)
        verification.verify(expected=expected, actual=actual)
        self._uow.verifications.add(verification, command.tenant_id)
        return verification
