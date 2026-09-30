"""Transaction boundary abstraction."""
from typing import Protocol

from decision_os.application.ports.action_repository import ActionExecutionRepository, ActionRepository
from decision_os.application.ports.decision_case_repository import DecisionCaseRepository
from decision_os.application.ports.decision_option_repository import DecisionOptionRepository
from decision_os.application.ports.decision_repository import DecisionRepository
from decision_os.application.ports.outcome_repository import ActualOutcomeRepository, ExpectedOutcomeRepository, VerificationRepository


class UnitOfWork(Protocol):
    decision_cases: DecisionCaseRepository
    decision_options: DecisionOptionRepository
    decisions: DecisionRepository
    actions: ActionRepository
    action_executions: ActionExecutionRepository
    expected_outcomes: ExpectedOutcomeRepository
    actual_outcomes: ActualOutcomeRepository
    verifications: VerificationRepository

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
