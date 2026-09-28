"""Generic application reliability execution primitive.

The executor owns transaction/reliability mechanics while command-specific
boundaries retain request hashing, response serialization, audit and outbox
semantics.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Generic, TypeVar
from uuid import UUID, uuid4

from decision_os.application.ports.audit import AuditEvent, AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxMessage, OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork

TCommand = TypeVar("TCommand")
TResult = TypeVar("TResult")


@dataclass(frozen=True)
class ReliabilitySpec(Generic[TCommand, TResult]):
    operation: str
    response_status: int
    tenant_id: Callable[[TCommand], UUID]
    request_hash: Callable[[TCommand], str]
    actor_id: Callable[[TCommand], UUID]
    execute: Callable[[TCommand], TResult]
    entity_id: Callable[[TResult], UUID]
    entity_type: str
    serialize: Callable[[TResult], str]
    deserialize: Callable[[str], TResult]
    outbox_topic: str
    outbox_payload: Callable[[TResult], str]


class ReliabilityExecutor(Generic[TCommand, TResult]):
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        idempotency: IdempotencyPort,
        audit: AuditPort,
        outbox: OutboxPort,
    ) -> None:
        self._uow = uow
        self._idempotency = idempotency
        self._audit = audit
        self._outbox = outbox

    def execute(
        self,
        command: TCommand,
        *,
        spec: ReliabilitySpec[TCommand, TResult],
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ) -> TResult:
        tenant_id = spec.tenant_id(command)
        record = self._idempotency.reserve(
            tenant_id=tenant_id,
            operation=spec.operation,
            key=idempotency_key,
            request_hash=spec.request_hash(command),
        )
        if record.status == "COMPLETED":
            return spec.deserialize(record.response_body or "")

        correlation_id = correlation_id or uuid4()
        try:
            result = spec.execute(command)
            now = datetime.now(timezone.utc)
            entity_id = spec.entity_id(result)
            self._audit.append(
                AuditEvent(
                    tenant_id=tenant_id,
                    actor_id=spec.actor_id(command),
                    action=spec.operation,
                    entity_type=spec.entity_type,
                    entity_id=entity_id,
                    occurred_at=now,
                    correlation_id=correlation_id,
                )
            )
            self._outbox.add(
                OutboxMessage(
                    id=uuid4(),
                    topic=spec.outbox_topic,
                    aggregate_type=spec.entity_type,
                    aggregate_id=entity_id,
                    payload=spec.outbox_payload(result),
                    occurred_at=now,
                )
            )
            self._idempotency.complete(
                tenant_id=tenant_id,
                operation=spec.operation,
                key=idempotency_key,
                response_status=spec.response_status,
                response_body=spec.serialize(result),
            )
            self._uow.commit()
            return result
        except Exception:
            self._uow.rollback()
            raise
