import hashlib
import json
from uuid import UUID

from decision_os.application.commands.mark_execution_unknown import MarkExecutionUnknownCommand, MarkExecutionUnknownHandler
from decision_os.application.ports.audit import AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec
from decision_os.domain.action import ActionExecution, ActionExecutionStatus


class MarkExecutionUnknownReliabilityBoundary:
    OPERATION = "MarkExecutionUnknown"
    RESPONSE_STATUS = 200

    def __init__(self, *, uow: UnitOfWork, handler: MarkExecutionUnknownHandler, idempotency: IdempotencyPort, audit: AuditPort, outbox: OutboxPort) -> None:
        self._executor = ReliabilityExecutor(uow=uow, idempotency=idempotency, audit=audit, outbox=outbox)
        self._handler = handler

    def execute(self, command: MarkExecutionUnknownCommand, *, idempotency_key: str, correlation_id: UUID | None = None) -> ActionExecution:
        return self._executor.execute(command, spec=ReliabilitySpec(
            operation=self.OPERATION, response_status=self.RESPONSE_STATUS,
            tenant_id=lambda value: value.tenant_id, request_hash=self._request_hash,
            actor_id=lambda value: value.actor_id, execute=self._handler.handle,
            entity_id=lambda value: value.id, entity_type="ActionExecution",
            serialize=self._serialize, deserialize=self._deserialize,
            outbox_topic="decision.action-execution-unknown",
            outbox_payload=lambda value: json.dumps({"execution_id": str(value.id), "action_id": str(value.action_id), "attempt": value.attempt, "status": value.status.value}, sort_keys=True),
        ), idempotency_key=idempotency_key, correlation_id=correlation_id)

    @staticmethod
    def _request_hash(command: MarkExecutionUnknownCommand) -> str:
        payload={"tenant_id":str(command.tenant_id),"execution_id":str(command.execution_id),"actor_id":str(command.actor_id)}
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

    @staticmethod
    def _serialize(value: ActionExecution) -> str:
        return json.dumps({"id":str(value.id),"action_id":str(value.action_id),"attempt":value.attempt,"status":value.status.value},sort_keys=True)

    @staticmethod
    def _deserialize(body: str) -> ActionExecution:
        if not body: raise RuntimeError("completed idempotency record has no response")
        data=json.loads(body)
        return ActionExecution(id=UUID(data["id"]),action_id=UUID(data["action_id"]),attempt=int(data["attempt"]),status=ActionExecutionStatus(data["status"]))
