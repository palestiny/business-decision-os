"""Port for DecisionOption persistence."""
from typing import Protocol
from uuid import UUID

from decision_os.domain.decision import DecisionOption


class DecisionOptionRepository(Protocol):
    def list_for_case(self, *, case_id: UUID, tenant_id: UUID) -> tuple[DecisionOption, ...]:
        ...
