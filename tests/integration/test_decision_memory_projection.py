from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, close_all_sessions

from decision_os.domain.decision import Decision, DecisionOption
from decision_os.domain.decision_case import CaseStatus, DecisionCase
from decision_os.infrastructure.persistence.models.decision import DecisionModel, DecisionOptionModel
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel
from decision_os.infrastructure.persistence.models.decision_memory import DecisionMemoryProjectionModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.repositories.decision_case import SQLAlchemyDecisionCaseRepository
from decision_os.infrastructure.persistence.session import build_session_factory
from decision_os.infrastructure.persistence.projectors.decision_memory import SQLAlchemyDecisionMemoryProjector
from decision_os.infrastructure.persistence.models.action import ActionModel, ActionExecutionModel
from decision_os.infrastructure.persistence.models.outcome import ExpectedOutcomeModel, ActualOutcomeModel, VerificationModel
from decision_os.infrastructure.persistence.models.evidence import EvidenceModel, AnalysisFindingModel

import os

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests")


@pytest.fixture()
def session():
    factory = build_session_factory(DATABASE_URL)
    with factory() as db:
        yield db
        db.rollback()
    close_all_sessions()


def seed_tenant(session: Session, tenant_id):
    session.add(TenantModel(id=tenant_id, name="decision-memory-test"))
    session.commit()


def seed_case(session: Session, tenant_id, *, status=CaseStatus.DECISION_MADE, version=1):
    case = DecisionCase.create(id=uuid4(), tenant_id=tenant_id, case_type="PROJECT_MARGIN_RISK", title="Memory projection case")
    case.status = status
    case.version = version
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.flush()
    return case


def test_projector_reads_authoritative_state_and_is_tenant_scoped(session: Session):
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    actor_id = uuid4()
    seed_tenant(session, tenant_id)
    seed_tenant(session, other_tenant_id)
    case = seed_case(session, tenant_id)

    option = DecisionOption(id=uuid4(), case_id=case.id, title="Protect margin")
    session.add(DecisionOptionModel(id=option.id, case_id=case.id, title=option.title))
    decision = Decision.make(
        id=uuid4(), case_id=case.id, available_options=(option,), selected_option_ids=(option.id,),
        rationale="Protect delivery margin.", decided_by=actor_id, approval_required=True,
    )
    session.add(DecisionModel(
        id=decision.id, case_id=case.id, status=decision.status.value, rationale=decision.rationale,
        decided_by=decision.decided_by, decided_at=datetime.now(timezone.utc), approval_required=True,
        created_at=datetime.now(timezone.utc),
    ))
    from decision_os.infrastructure.persistence.models.decision import DecisionSelectedOptionModel
    session.add(DecisionSelectedOptionModel(decision_id=decision.id, option_id=option.id))
    evidence_id = uuid4()
    session.add(EvidenceModel(id=evidence_id, tenant_id=tenant_id, case_id=case.id, source="PSA", metric="margin", value="12", unit="percent", period="2026-10", captured_at=datetime.now(timezone.utc), confidence=0.95, snapshot="margin=12"))
    finding_id = uuid4()
    session.add(AnalysisFindingModel(id=finding_id, tenant_id=tenant_id, case_id=case.id, kind="INFERENCE", statement="Margin is below threshold.", confidence=0.9, evidence_ids='["%s"]' % evidence_id))
    action_id = uuid4()
    session.add(ActionModel(id=action_id, tenant_id=tenant_id, case_id=case.id, decision_id=decision.id, action_type="REDUCE_SCOPE", parameters="scope-10", status="COMPLETED", version=1))
    session.add(ActionExecutionModel(id=uuid4(), action_id=action_id, attempt=1, status="SUCCEEDED"))
    expected_id = uuid4()
    session.add(ExpectedOutcomeModel(id=expected_id, tenant_id=tenant_id, case_id=case.id, metric="gross_margin", operator="GTE", target="20"))
    actual_id = uuid4()
    session.add(ActualOutcomeModel(id=actual_id, tenant_id=tenant_id, case_id=case.id, expected_outcome_id=expected_id, observed_value="22", status="RECORDED"))
    verification_id = uuid4()
    session.add(VerificationModel(id=verification_id, tenant_id=tenant_id, case_id=case.id, actual_outcome_id=actual_id, status="PASS"))
    session.commit()

    snapshot = SQLAlchemyDecisionMemoryProjector(session).project(tenant_id=tenant_id, case_id=case.id)
    projection = session.scalar(select(DecisionMemoryProjectionModel).where(DecisionMemoryProjectionModel.tenant_id == tenant_id, DecisionMemoryProjectionModel.case_id == case.id))

    assert snapshot.authoritative_version == case.version
    assert projection is not None
    assert projection.decision_id == decision.id
    assert projection.selected_option_ids == [str(option.id)]
    assert projection.action_summary["type"] == "REDUCE_SCOPE"
    assert projection.outcome_summary["actual"]["observed_value"] == "22"
    assert projection.verification_summary["status"] == "PASS"
    assert str(evidence_id) in projection.source_ids["evidence_ids"]
    assert str(finding_id) in projection.source_ids["analysis_finding_ids"]

    with pytest.raises(ValueError, match="decision case not found"):
        SQLAlchemyDecisionMemoryProjector(session).project(tenant_id=other_tenant_id, case_id=case.id)


def test_duplicate_and_out_of_order_notifications_are_harmless(session: Session):
    tenant_id = uuid4()
    seed_tenant(session, tenant_id)
    case = seed_case(session, tenant_id, status=CaseStatus.DETECTED, version=0)
    projector = SQLAlchemyDecisionMemoryProjector(session)

    projector.project(tenant_id=tenant_id, case_id=case.id, notified_version=0)
    case_model = session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case.id))
    assert case_model is not None
    case_model.status = CaseStatus.CLOSED.value
    case_model.version = 5
    session.commit()

    projector.project(tenant_id=tenant_id, case_id=case.id, notified_version=5)
    projection = session.scalar(select(DecisionMemoryProjectionModel).where(DecisionMemoryProjectionModel.tenant_id == tenant_id, DecisionMemoryProjectionModel.case_id == case.id))
    assert projection is not None
    assert projection.authoritative_version == 5
    assert projection.case_status == CaseStatus.CLOSED.value

    projector.project(tenant_id=tenant_id, case_id=case.id, notified_version=1)
    projection = session.scalar(select(DecisionMemoryProjectionModel).where(DecisionMemoryProjectionModel.tenant_id == tenant_id, DecisionMemoryProjectionModel.case_id == case.id))
    assert projection is not None
    assert projection.authoritative_version == 5
    assert projection.case_status == CaseStatus.CLOSED.value


def test_projection_failure_does_not_change_authoritative_case(session: Session):
    tenant_id = uuid4()
    seed_tenant(session, tenant_id)
    case = seed_case(session, tenant_id, status=CaseStatus.CLOSED, version=11)
    session.commit()

    with pytest.raises(ValueError, match="decision case not found"):
        SQLAlchemyDecisionMemoryProjector(session).project(tenant_id=tenant_id, case_id=uuid4())

    persisted = session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case.id, DecisionCaseModel.tenant_id == tenant_id))
    assert persisted is not None
    assert persisted.status == CaseStatus.CLOSED.value
    assert persisted.version == 11


def test_rebuild_reconstructs_current_authoritative_projection(session: Session):
    tenant_id = uuid4()
    seed_tenant(session, tenant_id)
    case = seed_case(session, tenant_id, status=CaseStatus.DECISION_MADE, version=4)
    projector = SQLAlchemyDecisionMemoryProjector(session)
    projector.project(tenant_id=tenant_id, case_id=case.id)

    projection = session.scalar(select(DecisionMemoryProjectionModel).where(DecisionMemoryProjectionModel.tenant_id == tenant_id, DecisionMemoryProjectionModel.case_id == case.id))
    assert projection is not None
    projection.case_title = "stale projection"
    projection.authoritative_version = 1
    session.commit()

    rebuilt = projector.rebuild(tenant_id=tenant_id, case_id=case.id)
    assert rebuilt.authoritative_version == 4
    refreshed = session.scalar(select(DecisionMemoryProjectionModel).where(DecisionMemoryProjectionModel.tenant_id == tenant_id, DecisionMemoryProjectionModel.case_id == case.id))
    assert refreshed is not None
    assert refreshed.case_title == case.title
    assert refreshed.authoritative_version == 4
