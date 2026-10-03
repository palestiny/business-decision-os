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


@dataclass(frozen=True)
class DecisionMemoryView:
    tenant_id: UUID
    case_id: UUID
    case_type: str
    case_title: str
    case_status: str
    decision_id: UUID | None
    decision_status: str | None
    rationale: str | None
    decided_by: UUID | None
    selected_option_ids: tuple[UUID, ...]
    approval_required: bool | None
    action_summary: dict | None
    outcome_summary: dict | None
    verification_summary: dict | None
    source_ids: dict
    authoritative_version: int
    notified_version: int | None
    projected_version: int | None
    projected_at: datetime
    state: str


class DecisionMemoryProjector(Protocol):
    def project(self, *, tenant_id: UUID, case_id: UUID, notified_version: int | None = None) -> DecisionMemorySnapshot:
        """Project the current authoritative state; notification payload is never authoritative."""

    def rebuild(self, *, tenant_id: UUID, case_id: UUID) -> DecisionMemorySnapshot:
        """Rebuild from current authoritative Decision Core state."""


class DecisionMemoryReader(Protocol):
    def get(self, *, tenant_id: UUID, case_id: UUID) -> DecisionMemoryView | None:
        """Read a tenant-scoped Decision Memory projection."""
