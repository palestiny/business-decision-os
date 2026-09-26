"""Application reliability boundary for externally retryable commands."""
import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from decision_os.application.commands.create_decision_case import (
    CreateDecisionCaseCommand,
    CreateDecisionCaseHandler,
)
from decision_os.application.ports.audit import AuditEvent, AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxMessage, OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.decision_case import DecisionCase


class CreateDecisionCaseReliabilityBoundary:
    """Proof implementation of the command reliability contract for case creation."""

    OPERATION = "CreateDecisionCase"
    RESPONSE_STATUS = 201

    def __init__(
        self,
        *,
        uow: UnitOfWork,
        handler: CreateDecisionCaseHandler,
        idempotency: IdempotencyPort,
        audit: AuditPort,
        outbox: OutboxPort,
    ) -> None:
        self._uow = uow
        self._handler = handler
        self._idempotency = idempotency
        self._audit = audit
        self._outbox = outbox

    def execute(
        self,
        command: CreateDecisionCaseCommand,
        *,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ) -> DecisionCase:
        request_hash = self._request_hash(command)
        record = self._idempotency.reserve(
            tenant_id=command.tenant_id,
            operation=self.OPERATION,
            key=idempotency_key,
            request_hash=request_hash,
        )
        if record.status == "COMPLETED":
            return self._deserialize_case(record.response_body)

        correlation_id = correlation_id or uuid4()
        try:
            case = self._handler.handle(command, commit=False)
            now = datetime.now(timezone.utc)
            self._audit.append(
                AuditEvent(
                    tenant_id=case.tenant_id,
                    actor_id=command.actor_id,
                    action=self.OPERATION,
                    entity_type="DecisionCase",
                    entity_id=case.id,
                    occurred_at=now,
                    correlation_id=correlation_id,
                )
            )
            self._outbox.add(
                OutboxMessage(
                    id=uuid4(),
                    topic="decision-case.created",
                    aggregate_type="DecisionCase",
                    aggregate_id=case.id,
                    payload=json.dumps(
                        {"case_id": str(case.id), "tenant_id": str(case.tenant_id)},
                        sort_keys=True,
                    ),
                    occurred_at=now,
                )
            )
            response_body = self._serialize_case(case)
            self._idempotency.complete(
                tenant_id=command.tenant_id,
                operation=self.OPERATION,
                key=idempotency_key,
                response_status=self.RESPONSE_STATUS,
                response_body=response_body,
            )
            self._uow.commit()
            return case
        except Exception:
            self._uow.rollback()
            raise

    @staticmethod
    def _request_hash(command: CreateDecisionCaseCommand) -> str:
        payload = json.dumps(
            {
                "tenant_id": str(command.tenant_id),
                "case_type": command.case_type,
                "title": command.title,
                "actor_id": str(command.actor_id),
                "case_id": str(command.case_id) if command.case_id else None,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _serialize_case(case: DecisionCase) -> str:
        return json.dumps(
            {
                "id": str(case.id),
                "tenant_id": str(case.tenant_id),
                "case_type": case.case_type,
                "title": case.title,
                "status": case.status.value,
                "version": case.version,
            },
            sort_keys=True,
        )

    @staticmethod
    def _deserialize_case(body: str | None) -> DecisionCase:
        if not body:
            raise RuntimeError("completed idempotency record has no response")
        data = json.loads(body)
        from decision_os.domain.decision_case import CaseStatus

        return DecisionCase(
            id=UUID(data["id"]),
            tenant_id=UUID(data["tenant_id"]),
            case_type=data["case_type"],
            title=data["title"],
            status=CaseStatus(data["status"]),
            version=data["version"],
        )
