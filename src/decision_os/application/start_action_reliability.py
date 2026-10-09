import hashlib
import json
from uuid import UUID

from decision_os.application.commands.start_action import StartActionCommand, StartActionHandler
from decision_os.application.ports.audit import AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec
from decision_os.domain.action import ActionExecution, ActionExecutionStatus


class StartActionReliabilityBoundary:
    OPERATION = "StartAction"
    RESPONSE_STATUS = 200

    def __init__(self, *, uow: UnitOfWork, handler: StartActionHandler, idempotency: IdempotencyPort, audit: AuditPort, outbox: OutboxPort) -> None:
        self._executor = ReliabilityExecutor(uow=uow, idempotency=idempotency, audit=audit, outbox=outbox)
        self._handler = handler

    def execute(self, command: StartActionCommand, *, idempotency_key: str, correlation_id: UUID | None = None) -> ActionExecution:
        return self._executor.execute(command, spec=ReliabilitySpec(
            operation=self.OPERATION, response_status=self.RESPONSE_STATUS,
            tenant_id=lambda value: value.tenant_id, request_hash=self._request_hash,
            actor_id=lambda value: value.actor_id, execute=self._handler.handle,
            entity_id=lambda value: value.id, entity_type="ActionExecution",
            serialize=self._serialize, deserialize=self._deserialize,
            outbox_topic="decision.action-started",
            outbox_payload=lambda execution: json.dumps({
                "execution_id": str(execution.id), "action_id": str(execution.action_id),
                "attempt": execution.attempt, "status": execution.status.value,
            }, sort_keys=True),
        ), idempotency_key=idempotency_key, correlation_id=correlation_id)

    @staticmethod
    def _request_hash(command: StartActionCommand) -> str:
        payload={"tenant_id":str(command.tenant_id),"action_id":str(command.action_id),"actor_id":str(command.actor_id),
                 "execution_id":str(command.execution_id) if command.execution_id else None}
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

    @staticmethod
    def _serialize(execution: ActionExecution) -> str:
        return json.dumps({"id":str(execution.id),"action_id":str(execution.action_id),
                           "attempt":execution.attempt,"status":execution.status.value},sort_keys=True)

    @staticmethod
    def _deserialize(body: str | None) -> ActionExecution:
        if not body: raise RuntimeError("completed idempotency record has no response")
        data=json.loads(body)
        return ActionExecution(id=UUID(data["id"]),action_id=UUID(data["action_id"]),
                               attempt=int(data["attempt"]),status=ActionExecutionStatus(data["status"]))
