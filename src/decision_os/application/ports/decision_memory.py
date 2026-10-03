from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Protocol


@dataclass(frozen=True)
class DecisionMemorySnapshot:
    tenant_id: UUID
    case_id: UUID
    authoritative_version: int
    projected_at: datetime
    state: str


class DecisionMemoryProjector(Protocol):
    def project(self, *, tenant_id: UUID, case_id: UUID, notified_version: int | None = None) -> DecisionMemorySnapshot:
        """Project the current authoritative state; notification payload is never authoritative."""

    def rebuild(self, *, tenant_id: UUID, case_id: UUID) -> DecisionMemorySnapshot:
        """Rebuild from current authoritative Decision Core state."""
