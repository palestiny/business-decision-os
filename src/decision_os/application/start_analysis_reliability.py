"""Application reliability boundary for starting case analysis."""
import hashlib
import json
from uuid import UUID

from decision_os.application.commands.start_analysis import StartAnalysisCommand, StartAnalysisHandler
from decision_os.application.ports.audit import AuditPort
from decision_os.application.ports.idempotency import IdempotencyPort
from decision_os.application.ports.outbox import OutboxPort
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec
from decision_os.domain.decision_case import DecisionCase, CaseStatus


class StartAnalysisReliabilityBoundary:
    OPERATION = "StartAnalysis"
    RESPONSE_STATUS = 200

    def __init__(self, *, uow: UnitOfWork, handler: StartAnalysisHandler, idempotency: IdempotencyPort, audit: AuditPort, outbox: OutboxPort) -> None:
        self._executor = ReliabilityExecutor(uow=uow, idempotency=idempotency, audit=audit, outbox=outbox)
        self._handler = handler

    def execute(self, command: StartAnalysisCommand, *, idempotency_key: str, correlation_id: UUID | None = None) -> DecisionCase:
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
                serialize=self._serialize,
                deserialize=self._deserialize,
                outbox_topic="decision-case.analysis-started",
                outbox_payload=lambda case: json.dumps(
                    {"case_id": str(case.id), "status": case.status.value, "version": case.version},
                    sort_keys=True,
                ),
            ),
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    @staticmethod
    def _request_hash(command: StartAnalysisCommand) -> str:
        payload = json.dumps({"tenant_id": str(command.tenant_id), "case_id": str(command.case_id), "actor_id": str(command.actor_id)}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _serialize(case: DecisionCase) -> str:
        return json.dumps({"id": str(case.id), "tenant_id": str(case.tenant_id), "case_type": case.case_type, "title": case.title, "status": case.status.value, "version": case.version}, sort_keys=True)

    @staticmethod
    def _deserialize(body: str | None) -> DecisionCase:
        if not body:
            raise RuntimeError("completed idempotency record has no response")
        data = json.loads(body)
        return DecisionCase(id=UUID(data["id"]), tenant_id=UUID(data["tenant_id"]), case_type=data["case_type"], title=data["title"], status=CaseStatus(data["status"]), version=int(data["version"]))
