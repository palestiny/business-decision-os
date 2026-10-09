from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.analysis import AnalysisFinding, AnalysisKind, InvalidAnalysis


@dataclass(frozen=True)
class AddAnalysisFindingCommand:
    tenant_id: UUID
    case_id: UUID
    actor_id: UUID
    finding_id: UUID
    kind: AnalysisKind
    statement: str
    confidence: float
    evidence_ids: tuple[UUID, ...]
    correlation_id: UUID | None = None

class AddAnalysisFindingHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: AddAnalysisFindingCommand) -> AnalysisFinding:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise InvalidAnalysis("decision case not found")
        if case.status.value != "ANALYZING":
            raise InvalidAnalysis("case is not in analysis")
        self._authorization.require(actor_id=command.actor_id, tenant_id=command.tenant_id, permission=Permission.ADD_ANALYSIS, resource_id=case.id, correlation_id=command.correlation_id)
        evidence = {item.id for item in self._uow.evidence.list_for_case(case.id, command.tenant_id)}
        if any(item not in evidence for item in command.evidence_ids):
            raise InvalidAnalysis("analysis references unknown evidence")
        finding = AnalysisFinding.create(
            id=command.finding_id, case_id=case.id, kind=command.kind,
            statement=command.statement, confidence=command.confidence, evidence_ids=command.evidence_ids,
        )
        self._uow.analysis_findings.add(finding, command.tenant_id)
        return finding
