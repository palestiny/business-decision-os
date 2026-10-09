from datetime import datetime, timezone
from typing import Protocol

from decision_os.application.ports.decision_memory import DecisionMemoryProjector
from decision_os.application.ports.outbox import OutboxPublicationPort, OutboxRecord, OutboxRepositoryPort, PublicationTransactionPort


class OutboxProcessor:
    """Processes transactional outbox records without making payload the business source of truth."""

    def __init__(
        self,
        *,
        repository: OutboxRepositoryPort,
        publication: OutboxPublicationPort,
        transaction: PublicationTransactionPort,
        decision_memory: DecisionMemoryProjector,
    ) -> None:
        self._repository = repository
        self._publication = publication
        self._transaction = transaction
        self._decision_memory = decision_memory

    def process(self, *, limit: int = 100) -> int:
        records = self._repository.get_unpublished(limit=limit)
        processed = 0
        for record in records:
            try:
                self._publication.publish(record)
                if record.aggregate_type == "DecisionCase" and record.tenant_id is not None:
                    self._decision_memory.project(
                        tenant_id=record.tenant_id,
                        case_id=record.aggregate_id,
                    )
                self._repository.mark_published(
                    message_id=record.id,
                    published_at=datetime.now(timezone.utc),
                )
                self._transaction.commit()
                processed += 1
            except Exception:
                self._transaction.rollback()
                raise
        return processed
