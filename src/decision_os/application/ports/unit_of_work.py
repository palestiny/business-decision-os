"""Transaction boundary abstraction."""
from typing import Protocol

from decision_os.application.ports.decision_case_repository import (
    DecisionCaseRepository,
)


class UnitOfWork(Protocol):
    decision_cases: DecisionCaseRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
