from dataclasses import dataclass
from uuid import UUID
from typing import Protocol


@dataclass(frozen=True)
class DecisionWorkQueueItem:
    tenant_id: UUID
    case_id: UUID
    case_type: str
    title: str
    case_status: str
    attention_state: str
    decision_id: UUID | None
    decision_status: str | None
    approval_required: bool | None
    authoritative_version: int
    projection_state: str | None


class DecisionWorkQueueReader(Protocol):
    def list(self, *, tenant_id: UUID) -> tuple[DecisionWorkQueueItem, ...]:
        """Return deterministic, tenant-scoped cases requiring human attention."""
