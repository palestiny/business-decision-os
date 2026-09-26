"""Port for Decision persistence."""
from typing import Protocol
from uuid import UUID

from decision_os.domain.decision import Decision


class DecisionRepository(Protocol):
    def get(self, decision_id: UUID, tenant_id: UUID) -> Decision | None:
        ...

    def add(self, decision: Decision) -> None:
        ...

    def save(self, decision: Decision, tenant_id: UUID) -> None:
        ...
