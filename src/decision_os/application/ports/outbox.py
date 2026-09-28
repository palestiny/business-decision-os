"""Transactional outbox and publication boundaries."""
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


@dataclass(frozen=True)
class OutboxRecord:
    id: UUID
    topic: str
    aggregate_type: str
    aggregate_id: UUID
    payload: str
    occurred_at: datetime
    published_at: datetime | None


class OutboxPublicationPort(Protocol):
    def publish(self, message: OutboxRecord) -> None:
        ...


class OutboxRepositoryPort(Protocol):
    def get_unpublished(self, *, limit: int = 100) -> tuple[OutboxRecord, ...]:
        ...

    def mark_published(self, *, message_id: UUID, published_at: datetime) -> None:
        ...
