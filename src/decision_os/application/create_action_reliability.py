import hashlib
import json
from uuid import UUID

from decision_os.application.commands.create_action import CreateActionCommand, CreateActionHandler
from decision_os.application.ports.audit import AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec
from decision_os.domain.action import Action, ActionStatus


class CreateActionReliabilityBoundary:
    OPERATION = "CreateAction"
    RESPONSE_STATUS = 201

    def __init__(self, *, uow: UnitOfWork, handler: CreateActionHandler, idempotency: IdempotencyPort, audit: AuditPort, outbox: OutboxPort) -> None:
        self._executor = ReliabilityExecutor(uow=uow, idempotency=idempotency, audit=audit, outbox=outbox)
        self._handler = handler

    def execute(self, command: CreateActionCommand, *, idempotency_key: str, correlation_id: UUID | None = None) -> Action:
        return self._executor.execute(command, spec=ReliabilitySpec(
            operation=self.OPERATION, response_status=self.RESPONSE_STATUS,
            tenant_id=lambda value: value.tenant_id, request_hash=self._request_hash,
            actor_id=lambda value: value.actor_id, execute=self._handler.handle,
            entity_id=lambda value: value.id, entity_type="Action",
            serialize=self._serialize, deserialize=self._deserialize,
            outbox_topic="decision.action-created",
            outbox_payload=lambda action: json.dumps({
                "action_id": str(action.id), "case_id": str(action.case_id),
                "decision_id": str(action.decision_id), "status": action.status.value,
            }, sort_keys=True),
        ), idempotency_key=idempotency_key, correlation_id=correlation_id)

    @staticmethod
    def _request_hash(command: CreateActionCommand) -> str:
        payload = {"tenant_id":str(command.tenant_id),"case_id":str(command.case_id),"decision_id":str(command.decision_id),
                   "actor_id":str(command.actor_id),"action_type":command.action_type,"parameters":command.parameters,
                   "action_id":str(command.action_id) if command.action_id else None}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",",":")).encode()).hexdigest()

    @staticmethod
    def _serialize(action: Action) -> str:
        return json.dumps({"id":str(action.id),"tenant_id":str(action.tenant_id),"case_id":str(action.case_id),
                           "decision_id":str(action.decision_id),"action_type":action.action_type,
                           "parameters":action.parameters,"status":action.status.value,"version":action.version}, sort_keys=True)

    @staticmethod
    def _deserialize(body: str | None) -> Action:
        if not body: raise RuntimeError("completed idempotency record has no response")
        data=json.loads(body)
        return Action(id=UUID(data["id"]),tenant_id=UUID(data["tenant_id"]),case_id=UUID(data["case_id"]),
                      decision_id=UUID(data["decision_id"]),action_type=data["action_type"],parameters=data["parameters"],
                      status=ActionStatus(data["status"]),version=int(data["version"]))
