from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.evidence import Evidence, InvalidEvidence


@dataclass(frozen=True)
class CreateEvidenceCommand:
    tenant_id: UUID
    case_id: UUID
    actor_id: UUID
    evidence_id: UUID
    source: str
    metric: str
    value: str
    unit: str
    period: str
    captured_at: datetime
    confidence: float
    snapshot: str


class CreateEvidenceHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: CreateEvidenceCommand) -> Evidence:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise InvalidEvidence("decision case not found")
        if case.status.value not in {"TRIAGED", "ANALYZING"}:
            raise InvalidEvidence("case is not ready to receive evidence")
        self._authorization.require(actor_id=command.actor_id, tenant_id=command.tenant_id, permission=Permission.CREATE_EVIDENCE, resource_id=case.id)
        evidence = Evidence.create(
            id=command.evidence_id, case_id=case.id, source=command.source, metric=command.metric,
            value=command.value, unit=command.unit, period=command.period,
            captured_at=command.captured_at, confidence=command.confidence, snapshot=command.snapshot,
        )
        self._uow.evidence.add(evidence, command.tenant_id)
        return evidence
