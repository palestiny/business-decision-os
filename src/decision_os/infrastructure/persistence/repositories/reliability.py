"""SQLAlchemy adapters for reliability ports."""
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from decision_os.application.ports.audit import AuditEvent
from decision_os.application.ports.idempotency import (
    IdempotencyConflict,
    IdempotencyRecord,
    RequestInProgress,
)
from decision_os.application.ports.outbox import OutboxMessage
from decision_os.infrastructure.persistence.models.reliability import (
    AuditEventModel,
    IdempotencyRecordModel,
    OutboxMessageModel,
)


class SQLAlchemyIdempotencyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def reserve(
        self,
        *,
        tenant_id: UUID,
        operation: str,
        key: str,
        request_hash: str,
    ) -> IdempotencyRecord:
        try:
            with self._session.begin_nested():
                self._session.add(
                    IdempotencyRecordModel(
                        tenant_id=tenant_id,
                        operation=operation,
                        key=key,
                        request_hash=request_hash,
                        status="IN_PROGRESS",
                        created_at=datetime.now(timezone.utc),
                    )
                )
                self._session.flush()
        except IntegrityError:
            existing = self._session.scalar(
                select(IdempotencyRecordModel).where(
                    IdempotencyRecordModel.tenant_id == tenant_id,
                    IdempotencyRecordModel.operation == operation,
                    IdempotencyRecordModel.key == key,
                )
            )
            if existing is None:
                raise
            if existing.request_hash != request_hash:
                raise IdempotencyConflict("idempotency key reused with a different request")
            if existing.status != "COMPLETED":
                raise RequestInProgress("idempotent request is already in progress")
            return self._to_record(existing)

        return IdempotencyRecord(
            tenant_id=tenant_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
            status="IN_PROGRESS",
        )

    def complete(
        self,
        *,
        tenant_id: UUID,
        operation: str,
        key: str,
        response_status: int,
        response_body: str,
    ) -> None:
        result = self._session.execute(
            update(IdempotencyRecordModel)
            .where(
                IdempotencyRecordModel.tenant_id == tenant_id,
                IdempotencyRecordModel.operation == operation,
                IdempotencyRecordModel.key == key,
                IdempotencyRecordModel.status == "IN_PROGRESS",
            )
            .values(
                status="COMPLETED",
                response_status=response_status,
                response_body=json.loads(response_body),
                completed_at=datetime.now(timezone.utc),
            )
        )
        if result.rowcount != 1:
            raise RuntimeError("idempotency record is not in progress")

    @staticmethod
    def _to_record(model: IdempotencyRecordModel) -> IdempotencyRecord:
        return IdempotencyRecord(
            tenant_id=model.tenant_id,
            operation=model.operation,
            key=model.key,
            request_hash=model.request_hash,
            status=model.status,
            response_status=model.response_status,
            response_body=json.dumps(model.response_body, sort_keys=True)
            if model.response_body is not None
            else None,
        )


class SQLAlchemyAuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, event: AuditEvent) -> None:
        self._session.add(
            AuditEventModel(
                id=uuid4(),
                tenant_id=event.tenant_id,
                actor_id=event.actor_id,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                occurred_at=event.occurred_at,
                correlation_id=event.correlation_id,
            )
        )


class SQLAlchemyOutboxRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, message: OutboxMessage) -> None:
        self._session.add(
            OutboxMessageModel(
                id=message.id,
                topic=message.topic,
                aggregate_type=message.aggregate_type,
                aggregate_id=message.aggregate_id,
                payload=json.loads(message.payload),
                occurred_at=message.occurred_at,
            )
        )
