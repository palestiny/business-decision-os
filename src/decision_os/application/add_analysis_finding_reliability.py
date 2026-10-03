import hashlib
import json
from uuid import UUID

from decision_os.application.commands.add_analysis_finding import AddAnalysisFindingCommand, AddAnalysisFindingHandler
from decision_os.application.ports.audit import AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec
from decision_os.domain.analysis import AnalysisFinding, AnalysisKind


class AddAnalysisFindingReliabilityBoundary:
    OPERATION = "AddAnalysisFinding"
    RESPONSE_STATUS = 201

    def __init__(self, *, uow: UnitOfWork, handler: AddAnalysisFindingHandler, idempotency: IdempotencyPort, audit: AuditPort, outbox: OutboxPort) -> None:
        self._executor = ReliabilityExecutor(uow=uow, idempotency=idempotency, audit=audit, outbox=outbox)
        self._handler = handler

    def execute(self, command: AddAnalysisFindingCommand, *, idempotency_key: str, correlation_id: UUID | None = None) -> AnalysisFinding:
        return self._executor.execute(
            command,
            spec=ReliabilitySpec(
                operation=self.OPERATION, response_status=self.RESPONSE_STATUS,
                tenant_id=lambda value: value.tenant_id, request_hash=self._request_hash,
                actor_id=lambda value: value.actor_id, execute=self._handler.handle,
                entity_id=lambda value: value.id, entity_type="AnalysisFinding",
                serialize=self._serialize, deserialize=self._deserialize,
                outbox_topic="decision.analysis-finding-added",
                outbox_payload=lambda value: json.dumps({"finding_id": str(value.id), "case_id": str(value.case_id), "kind": value.kind.value}, sort_keys=True),
            ),
            idempotency_key=idempotency_key, correlation_id=correlation_id,
        )

    @staticmethod
    def _request_hash(command: AddAnalysisFindingCommand) -> str:
        payload = {"tenant_id": str(command.tenant_id), "case_id": str(command.case_id), "actor_id": str(command.actor_id), "finding_id": str(command.finding_id), "kind": command.kind.value, "statement": command.statement, "confidence": command.confidence, "evidence_ids": [str(value) for value in command.evidence_ids]}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _serialize(value: AnalysisFinding) -> str:
        return json.dumps({"id": str(value.id), "case_id": str(value.case_id), "kind": value.kind.value, "statement": value.statement, "confidence": value.confidence, "evidence_ids": [str(item) for item in value.evidence_ids]}, sort_keys=True)

    @staticmethod
    def _deserialize(body: str) -> AnalysisFinding:
        data = json.loads(body)
        return AnalysisFinding(
            id=UUID(data["id"]), case_id=UUID(data["case_id"]), kind=AnalysisKind(data["kind"]),
            statement=data["statement"], confidence=float(data["confidence"]),
            evidence_ids=tuple(UUID(item) for item in data["evidence_ids"]),
        )
