import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, close_all_sessions

from decision_os.application.add_analysis_finding_reliability import AddAnalysisFindingReliabilityBoundary
from decision_os.application.commands.add_analysis_finding import AddAnalysisFindingCommand, AddAnalysisFindingHandler
from decision_os.application.commands.create_decision_case import CreateDecisionCaseCommand, CreateDecisionCaseHandler
from decision_os.application.commands.create_evidence import CreateEvidenceCommand, CreateEvidenceHandler
from decision_os.application.create_evidence_reliability import CreateEvidenceReliabilityBoundary
from decision_os.application.ports.authority import Permission
from decision_os.application.reliability import CreateDecisionCaseReliabilityBoundary
from decision_os.domain.analysis import AnalysisKind
from decision_os.domain.decision_case import CaseStatus, DecisionCase
from decision_os.infrastructure.persistence.models.analysis import AnalysisFindingModel
from decision_os.infrastructure.persistence.models.evidence import EvidenceModel
from decision_os.infrastructure.persistence.models.reliability import AuditEventModel, IdempotencyRecordModel, OutboxMessageModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.repositories.decision_case import SQLAlchemyDecisionCaseRepository
from decision_os.infrastructure.persistence.repositories.reliability import SQLAlchemyAuditRepository, SQLAlchemyIdempotencyRepository, SQLAlchemyOutboxRepository
from decision_os.infrastructure.persistence.session import build_session_factory
from decision_os.infrastructure.persistence.uow import SQLAlchemyUnitOfWork


DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests")


class AllowEvidenceAnalysisAuthorization:
    def require(self, *, permission, **kwargs):
        assert permission in {Permission.CREATE_EVIDENCE, Permission.ADD_ANALYSIS}


@pytest.fixture()
def session():
    factory = build_session_factory(DATABASE_URL)
    with factory() as db:
        yield db
        db.rollback()
    close_all_sessions()


def seed_case(session: Session):
    tenant_id, actor_id, case_id = uuid4(), uuid4(), uuid4()
    session.add(TenantModel(id=tenant_id, name="evidence-analysis-integration"))
    session.commit()
    case = DecisionCase(case_id, tenant_id, "PROJECT_MARGIN_RISK", "Margin risk", CaseStatus.ANALYZING, 2)
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.commit()
    return tenant_id, actor_id, case


def test_evidence_and_analysis_replay_persist_single_side_effects(session: Session):
    tenant_id, actor_id, case = seed_case(session)
    uow = SQLAlchemyUnitOfWork(session)
    auth = AllowEvidenceAnalysisAuthorization()
    idem = SQLAlchemyIdempotencyRepository(session)
    audit = SQLAlchemyAuditRepository(session)
    outbox = SQLAlchemyOutboxRepository(session)

    evidence_id = uuid4()
    evidence_boundary = CreateEvidenceReliabilityBoundary(
        uow=uow, handler=CreateEvidenceHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox
    )
    evidence_command = CreateEvidenceCommand(
        tenant_id=tenant_id, case_id=case.id, actor_id=actor_id, evidence_id=evidence_id,
        source="PSA", metric="gross_margin_percent", value="12.5", unit="percent",
        period="2026-09", captured_at=datetime.now(timezone.utc), confidence=0.95,
        snapshot="project-123:margin",
    )
    first = evidence_boundary.execute(evidence_command, idempotency_key="evidence-001")
    replay = evidence_boundary.execute(evidence_command, idempotency_key="evidence-001")
    assert replay.id == first.id

    finding_boundary = AddAnalysisFindingReliabilityBoundary(
        uow=uow, handler=AddAnalysisFindingHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox
    )
    finding_command = AddAnalysisFindingCommand(
        tenant_id=tenant_id, case_id=case.id, actor_id=actor_id, finding_id=uuid4(),
        kind=AnalysisKind.INFERENCE, statement="Margin erosion is present.",
        confidence=0.8, evidence_ids=(evidence_id,),
    )
    finding = finding_boundary.execute(finding_command, idempotency_key="finding-001")
    finding_replay = finding_boundary.execute(finding_command, idempotency_key="finding-001")
    assert finding_replay.id == finding.id

    assert session.scalar(select(EvidenceModel).where(EvidenceModel.id == evidence_id)) is not None
    assert session.scalar(select(AnalysisFindingModel).where(AnalysisFindingModel.id == finding.id)) is not None
    assert len(session.scalars(select(AuditEventModel).where(AuditEventModel.entity_id == evidence_id)).all()) == 1
    assert len(session.scalars(select(AuditEventModel).where(AuditEventModel.entity_id == finding.id)).all()) == 1
    assert len(session.scalars(select(OutboxMessageModel).where(OutboxMessageModel.aggregate_id == evidence_id)).all()) == 1
    assert len(session.scalars(select(OutboxMessageModel).where(OutboxMessageModel.aggregate_id == finding.id)).all()) == 1
    assert session.scalar(select(IdempotencyRecordModel).where(IdempotencyRecordModel.tenant_id == tenant_id, IdempotencyRecordModel.operation == "CreateEvidence", IdempotencyRecordModel.key == "evidence-001")).status == "COMPLETED"
    assert session.scalar(select(IdempotencyRecordModel).where(IdempotencyRecordModel.tenant_id == tenant_id, IdempotencyRecordModel.operation == "AddAnalysisFinding", IdempotencyRecordModel.key == "finding-001")).status == "COMPLETED"
