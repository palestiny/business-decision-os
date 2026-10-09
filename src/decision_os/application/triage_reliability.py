"""Application reliability boundary for case triage."""
import hashlib
import json
from uuid import UUID

from decision_os.application.commands.triage_case import TriageCaseCommand, TriageCaseHandler
from decision_os.application.ports.audit import AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec
from decision_os.domain.decision_case import CaseStatus, DecisionCase


class TriageCaseReliabilityBoundary:
    """Command-specific triage reliability contract backed by the generic executor."""

    OPERATION = "TriageCase"
    RESPONSE_STATUS = 200

    def __init__(
        self,
        *,
        uow: UnitOfWork,
        handler: TriageCaseHandler,
        idempotency: IdempotencyPort,
        audit: AuditPort,
        outbox: OutboxPort,
    ) -> None:
        self._uow = uow
        self._handler = handler
        self._idempotency = idempotency
        self._audit = audit
        self._outbox = outbox
        self._executor = ReliabilityExecutor(
            uow=uow,
            idempotency=idempotency,
            audit=audit,
            outbox=outbox,
        )

    def execute(
        self,
        command: TriageCaseCommand,
        *,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ) -> DecisionCase:
        return self._executor.execute(
            command,
            spec=ReliabilitySpec(
                operation=self.OPERATION,
                response_status=self.RESPONSE_STATUS,
                tenant_id=lambda value: value.tenant_id,
                request_hash=self._request_hash,
                actor_id=lambda value: value.actor_id,
                execute=self._handler.handle,
                entity_id=lambda value: value.id,
                entity_type="DecisionCase",
                serialize=self._serialize_case,
                deserialize=self._deserialize_case,
                outbox_topic="decision-case.triaged",
                outbox_payload=lambda case: json.dumps(
                    {
                        "case_id": str(case.id),
                        "tenant_id": str(case.tenant_id),
                        "status": case.status.value,
                    },
                    sort_keys=True,
                ),
            ),
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    @staticmethod
    def _request_hash(command: TriageCaseCommand) -> str:
        payload = json.dumps(
            {
                "tenant_id": str(command.tenant_id),
                "case_id": str(command.case_id),
                "actor_id": str(command.actor_id),
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
                "created_by": str(case.created_by) if case.created_by else None,
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
        return DecisionCase(
            id=UUID(data["id"]),
            tenant_id=UUID(data["tenant_id"]),
            case_type=data["case_type"],
            title=data["title"],
            created_by=UUID(data["created_by"]) if data.get("created_by") else None,
            status=CaseStatus(data["status"]),
            version=data["version"],
        )
