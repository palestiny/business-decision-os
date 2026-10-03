import hashlib
import json
from uuid import UUID

from decision_os.application.commands.record_actual_outcome import RecordActualOutcomeCommand, RecordActualOutcomeHandler
from decision_os.application.ports.audit import AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec
from decision_os.domain.outcome import ActualOutcome, OutcomeStatus


class RecordActualOutcomeReliabilityBoundary:
    OPERATION = "RecordActualOutcome"
    RESPONSE_STATUS = 201

    def __init__(self, *, uow: UnitOfWork, handler: RecordActualOutcomeHandler, idempotency: IdempotencyPort, audit: AuditPort, outbox: OutboxPort) -> None:
        self._executor = ReliabilityExecutor(uow=uow, idempotency=idempotency, audit=audit, outbox=outbox)
        self._handler = handler

    def execute(self, command: RecordActualOutcomeCommand, *, idempotency_key: str, correlation_id: UUID | None = None) -> ActualOutcome:
        return self._executor.execute(command, spec=ReliabilitySpec(
            operation=self.OPERATION, response_status=self.RESPONSE_STATUS,
            tenant_id=lambda v: v.tenant_id, request_hash=self._request_hash,
            actor_id=lambda v: v.actor_id, execute=self._handler.handle,
            entity_id=lambda v: v.id, entity_type="ActualOutcome",
            serialize=self._serialize, deserialize=self._deserialize,
            outbox_topic="decision.actual-outcome-recorded",
            outbox_payload=lambda v: json.dumps({"outcome_id": str(v.id), "case_id": str(v.case_id), "expected_outcome_id": str(v.expected_outcome_id), "observed_value": v.observed_value, "status": v.status.value}, sort_keys=True),
        ), idempotency_key=idempotency_key, correlation_id=correlation_id)

    @staticmethod
    def _request_hash(command: RecordActualOutcomeCommand) -> str:
        payload = {"tenant_id": str(command.tenant_id), "case_id": str(command.case_id), "actor_id": str(command.actor_id), "outcome_id": str(command.outcome_id), "expected_outcome_id": str(command.expected_outcome_id), "observed_value": command.observed_value}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _serialize(value: ActualOutcome) -> str:
        return json.dumps({"id": str(value.id), "case_id": str(value.case_id), "expected_outcome_id": str(value.expected_outcome_id), "observed_value": value.observed_value, "status": value.status.value}, sort_keys=True)

    @staticmethod
    def _deserialize(body: str | None) -> ActualOutcome:
        if not body:
            raise RuntimeError("completed idempotency record has no response")
        data = json.loads(body)
        return ActualOutcome(id=UUID(data["id"]), case_id=UUID(data["case_id"]), expected_outcome_id=UUID(data["expected_outcome_id"]), observed_value=float(data["observed_value"]), status=OutcomeStatus(data["status"]))
