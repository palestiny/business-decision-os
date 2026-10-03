"""Post-commit transactional-outbox publication service."""
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from decision_os.application.ports.outbox import (
    OutboxPublicationPort,
    OutboxRecord,
    OutboxRepositoryPort,
    PublicationTransactionPort,
)


class PublicationOutcomeUnknown(RuntimeError):
    """Delivery outcome cannot be confirmed after an external timeout/failure."""


@dataclass(frozen=True)
class PublicationResult:
    message_id: UUID
    published: bool
    outcome_known: bool


class OutboxPublicationService:
    """Publishes durable outbox records without coupling publication to DB commit."""

    def __init__(
        self,
        *,
        repository: OutboxRepositoryPort,
        publisher: OutboxPublicationPort,
        transaction: PublicationTransactionPort,
    ) -> None:
        self._repository = repository
        self._publisher = publisher
        self._transaction = transaction

    def publish_one(self, message: OutboxRecord) -> PublicationResult:
        if message.published_at is not None:
            return PublicationResult(message.id, True, True)

        try:
            self._publisher.publish(message)
        except PublicationOutcomeUnknown:
            return PublicationResult(message.id, False, False)

        try:
            self._repository.mark_published(
                message_id=message.id,
                published_at=datetime.now(timezone.utc),
            )
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise

        return PublicationResult(message.id, True, True)

    def publish_batch(self, *, limit: int = 100) -> tuple[PublicationResult, ...]:
        return tuple(
            self.publish_one(message)
            for message in self._repository.get_unpublished(limit=limit)
        )
