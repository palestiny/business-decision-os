from dataclasses import dataclass
from uuid import UUID
from typing import Protocol


class InvalidQueueCursor(ValueError):
    """The supplied cursor is malformed or uses an unsupported version."""


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


@dataclass(frozen=True)
class DecisionWorkQueuePage:
    items: tuple[DecisionWorkQueueItem, ...]
    next_cursor: str | None


class DecisionWorkQueueReader(Protocol):
    def list(
        self, *, tenant_id: UUID, limit: int = 50, cursor: str | None = None,
        attention_state: str | None = None, case_type: str | None = None,
    ) -> DecisionWorkQueuePage:
        """Return a bounded, deterministic, tenant-scoped queue page."""
