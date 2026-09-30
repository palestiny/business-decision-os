"""Transaction boundary abstraction."""
from typing import Protocol

from decision_os.application.ports.action_repository import ActionExecutionRepository, ActionRepository
from decision_os.application.ports.decision_case_repository import DecisionCaseRepository
from decision_os.application.ports.decision_option_repository import DecisionOptionRepository
from decision_os.application.ports.decision_repository import DecisionRepository


class UnitOfWork(Protocol):
    decision_cases: DecisionCaseRepository
    decision_options: DecisionOptionRepository
    decisions: DecisionRepository
    actions: ActionRepository
    action_executions: ActionExecutionRepository

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
