import hashlib
import json
from uuid import UUID

from decision_os.application.commands.create_evidence import CreateEvidenceCommand, CreateEvidenceHandler
from decision_os.application.ports.audit import AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec
from decision_os.domain.evidence import Evidence


class CreateEvidenceReliabilityBoundary:
    OPERATION = "CreateEvidence"
    RESPONSE_STATUS = 201

    def __init__(self, *, uow: UnitOfWork, handler: CreateEvidenceHandler, idempotency: IdempotencyPort, audit: AuditPort, outbox: OutboxPort) -> None:
        self._executor = ReliabilityExecutor(uow=uow, idempotency=idempotency, audit=audit, outbox=outbox)
        self._handler = handler

    def execute(self, command: CreateEvidenceCommand, *, idempotency_key: str, correlation_id: UUID | None = None) -> Evidence:
        return self._executor.execute(
            command,
            spec=ReliabilitySpec(
                operation=self.OPERATION, response_status=self.RESPONSE_STATUS,
                tenant_id=lambda value: value.tenant_id, request_hash=self._request_hash,
                actor_id=lambda value: value.actor_id, execute=self._handler.handle,
                entity_id=lambda value: value.id, entity_type="Evidence",
                serialize=self._serialize, deserialize=self._deserialize,
                outbox_topic="decision.evidence-created",
                outbox_payload=lambda value: json.dumps({"evidence_id": str(value.id), "case_id": str(value.case_id), "metric": value.metric, "value": value.value}, sort_keys=True),
            ),
            idempotency_key=idempotency_key, correlation_id=correlation_id,
        )

    @staticmethod
    def _request_hash(command: CreateEvidenceCommand) -> str:
        payload = {k: str(getattr(command, k)) for k in ("tenant_id", "case_id", "actor_id", "evidence_id", "source", "metric", "value", "unit", "period", "captured_at", "confidence", "snapshot")}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _serialize(value: Evidence) -> str:
        return json.dumps({
            "id": str(value.id), "case_id": str(value.case_id), "source": value.source, "metric": value.metric,
            "value": value.value, "unit": value.unit, "period": value.period, "captured_at": value.captured_at.isoformat(),
            "confidence": value.confidence, "snapshot": value.snapshot,
        }, sort_keys=True)

    @staticmethod
    def _deserialize(body: str) -> Evidence:
        from datetime import datetime
        data = json.loads(body)
        return Evidence(
            id=UUID(data["id"]), case_id=UUID(data["case_id"]), source=data["source"], metric=data["metric"],
            value=data["value"], unit=data["unit"], period=data["period"],
            captured_at=datetime.fromisoformat(data["captured_at"]), confidence=float(data["confidence"]),
            snapshot=data["snapshot"],
        )
