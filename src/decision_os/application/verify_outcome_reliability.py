import hashlib
import json
from uuid import UUID

from decision_os.application.commands.verify_outcome import VerifyOutcomeCommand, VerifyOutcomeHandler
from decision_os.application.ports.audit import AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec
from decision_os.domain.outcome import Verification, VerificationStatus


class VerifyOutcomeReliabilityBoundary:
    OPERATION = "VerifyOutcome"
    RESPONSE_STATUS = 200

    def __init__(self, *, uow: UnitOfWork, handler: VerifyOutcomeHandler, idempotency: IdempotencyPort, audit: AuditPort, outbox: OutboxPort) -> None:
        self._executor = ReliabilityExecutor(uow=uow, idempotency=idempotency, audit=audit, outbox=outbox)
        self._handler = handler

    def execute(self, command: VerifyOutcomeCommand, *, idempotency_key: str, correlation_id: UUID | None = None) -> Verification:
        return self._executor.execute(command, spec=ReliabilitySpec(
            operation=self.OPERATION, response_status=self.RESPONSE_STATUS,
            tenant_id=lambda v: v.tenant_id, request_hash=self._request_hash,
            actor_id=lambda v: v.actor_id, execute=self._handler.handle,
            entity_id=lambda v: v.id, entity_type="Verification",
            serialize=self._serialize, deserialize=self._deserialize,
            outbox_topic="decision.outcome-verified",
            outbox_payload=lambda v: json.dumps({"verification_id": str(v.id), "case_id": str(v.case_id), "actual_outcome_id": str(v.actual_outcome_id), "status": v.status.value}, sort_keys=True),
        ), idempotency_key=idempotency_key, correlation_id=correlation_id)

    @staticmethod
    def _request_hash(command: VerifyOutcomeCommand) -> str:
        payload = {"tenant_id": str(command.tenant_id), "case_id": str(command.case_id), "actor_id": str(command.actor_id), "verification_id": str(command.verification_id), "actual_outcome_id": str(command.actual_outcome_id)}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _serialize(value: Verification) -> str:
        return json.dumps({"id": str(value.id), "case_id": str(value.case_id), "actual_outcome_id": str(value.actual_outcome_id), "status": value.status.value}, sort_keys=True)

    @staticmethod
    def _deserialize(body: str | None) -> Verification:
        if not body:
            raise RuntimeError("completed idempotency record has no response")
        data = json.loads(body)
        return Verification(id=UUID(data["id"]), case_id=UUID(data["case_id"]), actual_outcome_id=UUID(data["actual_outcome_id"]), status=VerificationStatus(data["status"]))
