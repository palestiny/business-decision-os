import json
from uuid import UUID

from sqlalchemy import select

from decision_os.domain.analysis import AnalysisFinding, AnalysisKind
from decision_os.domain.evidence import Evidence
from decision_os.infrastructure.persistence.models.evidence import AnalysisFindingModel, EvidenceModel


class SQLAlchemyEvidenceRepository:
    def __init__(self, session) -> None:
        self._session = session

    def get(self, evidence_id: UUID, tenant_id: UUID) -> Evidence | None:
        row = self._session.execute(
            select(EvidenceModel).where(EvidenceModel.id == evidence_id, EvidenceModel.tenant_id == tenant_id)
        ).scalar_one_or_none()
        return None if row is None else Evidence(
            id=row.id, case_id=row.case_id, source=row.source, metric=row.metric, value=row.value,
            unit=row.unit, period=row.period, captured_at=row.captured_at, confidence=row.confidence,
            snapshot=row.snapshot,
        )

    def list_for_case(self, case_id: UUID, tenant_id: UUID) -> tuple[Evidence, ...]:
        rows = self._session.scalars(
            select(EvidenceModel)
            .where(EvidenceModel.case_id == case_id, EvidenceModel.tenant_id == tenant_id)
            .order_by(EvidenceModel.captured_at, EvidenceModel.id)
        ).all()
        return tuple(Evidence(
            id=row.id, case_id=row.case_id, source=row.source, metric=row.metric, value=row.value,
            unit=row.unit, period=row.period, captured_at=row.captured_at, confidence=row.confidence,
            snapshot=row.snapshot,
        ) for row in rows)

    def add(self, evidence: Evidence, tenant_id: UUID) -> None:
        self._session.add(EvidenceModel(
            id=evidence.id, tenant_id=tenant_id, case_id=evidence.case_id, source=evidence.source,
            metric=evidence.metric, value=evidence.value, unit=evidence.unit, period=evidence.period,
            captured_at=evidence.captured_at, confidence=evidence.confidence, snapshot=evidence.snapshot,
        ))


class SQLAlchemyAnalysisFindingRepository:
    def __init__(self, session) -> None:
        self._session = session

    def get(self, finding_id: UUID, tenant_id: UUID) -> AnalysisFinding | None:
        row = self._session.execute(
            select(AnalysisFindingModel).where(AnalysisFindingModel.id == finding_id, AnalysisFindingModel.tenant_id == tenant_id)
        ).scalar_one_or_none()
        return None if row is None else self._to_domain(row)

    def list_for_case(self, case_id: UUID, tenant_id: UUID) -> tuple[AnalysisFinding, ...]:
        rows = self._session.scalars(
            select(AnalysisFindingModel)
            .where(AnalysisFindingModel.case_id == case_id, AnalysisFindingModel.tenant_id == tenant_id)
            .order_by(AnalysisFindingModel.id)
        ).all()
        return tuple(self._to_domain(row) for row in rows)

    def add(self, finding: AnalysisFinding, tenant_id: UUID) -> None:
        self._session.add(AnalysisFindingModel(
            id=finding.id, tenant_id=tenant_id, case_id=finding.case_id, kind=finding.kind.value,
            statement=finding.statement, confidence=finding.confidence,
            evidence_ids=json.dumps([str(value) for value in finding.evidence_ids], sort_keys=True),
        ))

    @staticmethod
    def _to_domain(row: AnalysisFindingModel) -> AnalysisFinding:
        return AnalysisFinding(
            id=row.id, case_id=row.case_id, kind=AnalysisKind(row.kind),
            statement=row.statement, confidence=row.confidence,
            evidence_ids=tuple(UUID(value) for value in json.loads(row.evidence_ids)),
        )
