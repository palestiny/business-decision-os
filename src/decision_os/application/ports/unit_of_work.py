"""Transaction boundary abstraction."""
from typing import Protocol

from decision_os.application.ports.decision_case_repository import DecisionCaseRepository
from decision_os.application.ports.decision_repository import DecisionRepository


class UnitOfWork(Protocol):
    decision_cases: DecisionCaseRepository
    decisions: DecisionRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
