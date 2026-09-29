"""Reliability boundary for submitting decision options."""
import hashlib
import json
from uuid import UUID

from decision_os.application.commands.submit_options import SubmitOptionsCommand, SubmitOptionsHandler
from decision_os.application.ports.audit import AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec
from decision_os.application.commands.submit_options import SubmittedOptions


class SubmitOptionsReliabilityBoundary:
    OPERATION = "SubmitOptions"
    RESPONSE_STATUS = 200

    def __init__(self, *, uow: UnitOfWork, handler: SubmitOptionsHandler, idempotency: IdempotencyPort, audit: AuditPort, outbox: OutboxPort) -> None:
        self._executor = ReliabilityExecutor(uow=uow, idempotency=idempotency, audit=audit, outbox=outbox)
        self._handler = handler

    def execute(self, command: SubmitOptionsCommand, *, idempotency_key: str, correlation_id: UUID | None = None) -> SubmittedOptions:
        return self._executor.execute(
            command,
            spec=ReliabilitySpec(
                operation=self.OPERATION,
                response_status=self.RESPONSE_STATUS,
                tenant_id=lambda value: value.tenant_id,
                request_hash=self._request_hash,
                actor_id=lambda value: value.actor_id,
                execute=self._execute,
                entity_id=lambda value: value.case_id,
                entity_type="DecisionCase",
                serialize=self._serialize,
                deserialize=self._deserialize,
                outbox_topic="decision-case.options-submitted",
                outbox_payload=lambda value: json.dumps(
                    {"case_id": str(value.case_id), "option_ids": [str(o.id) for o in value.options], "status": value.status, "version": value.version},
                    sort_keys=True,
                ),
            ),
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    def _execute(self, command: SubmitOptionsCommand) -> SubmittedOptions:
        return self._handler.handle(command)

    @staticmethod
    def _request_hash(command: SubmitOptionsCommand) -> str:
        payload = json.dumps(
            {"tenant_id": str(command.tenant_id), "case_id": str(command.case_id), "actor_id": str(command.actor_id),
             "options": [{"id": str(option_id), "title": title} for option_id, title in command.options]},
            sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _serialize(value: SubmittedOptions) -> str:
        return json.dumps(
            {"case_id": str(value.case_id), "options": [{"id": str(o.id), "case_id": str(o.case_id), "title": o.title} for o in value.options],
             "status": value.status, "version": value.version},
            sort_keys=True,
        )

    @staticmethod
    def _deserialize(body: str | None) -> SubmittedOptions:
        if not body:
            raise RuntimeError("completed idempotency record has no response")
        data = json.loads(body)
        return SubmittedOptions(
            case_id=UUID(data["case_id"]),
            options=tuple(DecisionOption(id=UUID(o["id"]), case_id=UUID(o["case_id"]), title=o["title"]) for o in data["options"]),
            status=data["status"], version=int(data["version"]),
        )
