"""Ports for DecisionCase persistence."""
from typing import Protocol
from uuid import UUID

from decision_os.domain.decision_case import DecisionCase


class DecisionCaseRepository(Protocol):
    def get(self, case_id: UUID, tenant_id: UUID) -> DecisionCase | None:
        ...

    def add(self, case: DecisionCase) -> None:
        ...

    def save(self, case: DecisionCase) -> None:
        ...
