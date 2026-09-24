"""Append-only audit boundary."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class AuditEvent:
    tenant_id: UUID
    actor_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    occurred_at: datetime
    correlation_id: UUID


class AuditPort(Protocol):
    def append(self, event: AuditEvent) -> None:
        ...
