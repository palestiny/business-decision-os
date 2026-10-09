"""Application reliability boundary for rejecting decisions."""
import hashlib
import json
from datetime import datetime
from uuid import UUID

from decision_os.application.commands.reject_decision import RejectDecisionCommand, RejectDecisionHandler
from decision_os.application.ports.audit import AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec
from decision_os.domain.decision import Decision, DecisionStatus


class RejectDecisionReliabilityBoundary:
    OPERATION = "RejectDecision"
    RESPONSE_STATUS = 200

    def __init__(self, *, uow: UnitOfWork, handler: RejectDecisionHandler, idempotency: IdempotencyPort, audit: AuditPort, outbox: OutboxPort) -> None:
        self._handler = handler
        self._executor = ReliabilityExecutor(uow=uow, idempotency=idempotency, audit=audit, outbox=outbox)

    def execute(self, command: RejectDecisionCommand, *, idempotency_key: str, correlation_id: UUID | None = None) -> Decision:
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
                entity_type="Decision",
                serialize=self._serialize,
                deserialize=self._deserialize,
                outbox_topic="decision.rejected",
                outbox_payload=lambda decision: json.dumps(
                    {"decision_id": str(decision.id), "case_id": str(decision.case_id), "status": decision.status.value},
                    sort_keys=True,
                ),
            ),
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    @staticmethod
    def _request_hash(command: RejectDecisionCommand) -> str:
        payload = json.dumps(
            {"tenant_id": str(command.tenant_id), "case_id": str(command.case_id), "decision_id": str(command.decision_id), "actor_id": str(command.actor_id)},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _serialize(decision: Decision) -> str:
        return json.dumps(
            {
                "id": str(decision.id),
                "case_id": str(decision.case_id),
                "selected_option_ids": [str(value) for value in decision.selected_option_ids],
                "rationale": decision.rationale,
                "status": decision.status.value,
                "decided_by": str(decision.decided_by),
                "approval_required": decision.approval_required,
                "approved_by": str(decision.approved_by) if decision.approved_by else None,
                "approved_at": decision.approved_at.isoformat() if decision.approved_at else None,
                "policy_ids": [str(value) for value in decision.policy_ids],
            },
            sort_keys=True,
        )

    @staticmethod
    def _deserialize(body: str | None) -> Decision:
        if not body:
            raise RuntimeError("completed idempotency record has no response")
        data = json.loads(body)
        return Decision(
            id=UUID(data["id"]),
            case_id=UUID(data["case_id"]),
            selected_option_ids=tuple(UUID(value) for value in data["selected_option_ids"]),
            rationale=data["rationale"],
            status=DecisionStatus(data["status"]),
            decided_by=UUID(data["decided_by"]),
            _approval_required=bool(data["approval_required"]),
            approved_by=UUID(data["approved_by"]) if data.get("approved_by") else None,
            approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None,
            policy_ids=tuple(UUID(value) for value in data["policy_ids"]),
        )
