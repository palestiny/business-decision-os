"""Transactional outbox boundary."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class OutboxMessage:
    id: UUID
    topic: str
    aggregate_type: str
    aggregate_id: UUID
    payload: str
    occurred_at: datetime


class OutboxPort(Protocol):
    def add(self, message: OutboxMessage) -> None:
        ...
