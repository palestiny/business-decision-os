import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, close_all_sessions

from decision_os.application.add_analysis_finding_reliability import AddAnalysisFindingReliabilityBoundary
from decision_os.application.approve_decision_reliability import ApproveDecisionReliabilityBoundary
from decision_os.application.commands.add_analysis_finding import AddAnalysisFindingCommand, AddAnalysisFindingHandler
from decision_os.application.commands.approve_decision import ApproveDecisionCommand, ApproveDecisionHandler
from decision_os.application.commands.await_decision import AwaitDecisionCommand, AwaitDecisionHandler
from decision_os.application.commands.complete_action_execution import CompleteActionExecutionCommand, CompleteActionExecutionHandler
from decision_os.application.commands.create_action import CreateActionCommand, CreateActionHandler
from decision_os.application.commands.create_decision_case import CreateDecisionCaseCommand, CreateDecisionCaseHandler
from decision_os.application.commands.create_expected_outcome import CreateExpectedOutcomeCommand, CreateExpectedOutcomeHandler
from decision_os.application.commands.create_evidence import CreateEvidenceCommand, CreateEvidenceHandler
from decision_os.application.commands.make_decision import MakeDecisionCommand, MakeDecisionHandler
from decision_os.application.commands.record_actual_outcome import RecordActualOutcomeCommand, RecordActualOutcomeHandler
from decision_os.application.commands.start_action import StartActionCommand, StartActionHandler
from decision_os.application.commands.start_analysis import StartAnalysisCommand, StartAnalysisHandler
from decision_os.application.commands.submit_options import SubmitOptionsCommand, SubmitOptionsHandler
from decision_os.application.commands.triage_case import TriageCaseCommand, TriageCaseHandler
from decision_os.application.commands.verify_outcome import VerifyOutcomeCommand, VerifyOutcomeHandler
from decision_os.application.complete_action_execution_reliability import CompleteActionExecutionReliabilityBoundary
from decision_os.application.create_action_reliability import CreateActionReliabilityBoundary
from decision_os.application.create_expected_outcome_reliability import CreateExpectedOutcomeReliabilityBoundary
from decision_os.application.create_evidence_reliability import CreateEvidenceReliabilityBoundary
from decision_os.application.make_decision_reliability import MakeDecisionReliabilityBoundary
from decision_os.application.record_actual_outcome_reliability import RecordActualOutcomeReliabilityBoundary
from decision_os.application.start_action_reliability import StartActionReliabilityBoundary
from decision_os.application.start_analysis_reliability import StartAnalysisReliabilityBoundary
from decision_os.application.submit_options_reliability import SubmitOptionsReliabilityBoundary
from decision_os.application.triage_reliability import TriageCaseReliabilityBoundary
from decision_os.application.await_decision_reliability import AwaitDecisionReliabilityBoundary
from decision_os.application.verify_outcome_reliability import VerifyOutcomeReliabilityBoundary
from decision_os.application.ports.authority import ApprovalDecision, Permission
from decision_os.application.ports.reliability import IdempotencyRecord
from decision_os.application.reliability import CreateDecisionCaseReliabilityBoundary
from decision_os.domain.action import ActionExecutionStatus
from decision_os.domain.analysis import AnalysisKind
from decision_os.domain.decision_case import CaseStatus
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.repositories.decision_case import SQLAlchemyDecisionCaseRepository
from decision_os.infrastructure.persistence.repositories.reliability import SQLAlchemyAuditRepository, SQLAlchemyIdempotencyRepository, SQLAlchemyOutboxRepository
from decision_os.infrastructure.persistence.session import build_session_factory
from decision_os.infrastructure.persistence.uow import SQLAlchemyUnitOfWork


DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests")


class AllowAllAuthorization:
    def require(self, **kwargs):
        assert kwargs["permission"] in set(Permission)


class ApprovalPolicy:
    def __init__(self):
        self.policy_id = uuid4()

    def evaluate(self, **kwargs):
        return ApprovalDecision(required=True, policy_ids=(self.policy_id,))


@pytest.fixture()
def session():
    factory = build_session_factory(DATABASE_URL)
    with factory() as db:
        yield db
        db.rollback()
    close_all_sessions()


def test_project_margin_risk_full_closed_loop(session: Session):
    tenant_id, actor_id, case_id = uuid4(), uuid4(), uuid4()
    session.add(TenantModel(id=tenant_id, name="project-margin-vertical-slice"))
    session.commit()

    case = __import__("decision_os.domain.decision_case", fromlist=["DecisionCase"]).DecisionCase.create(
        id=case_id, tenant_id=tenant_id, case_type="PROJECT_MARGIN_RISK", title="Project Alpha margin risk"
    )
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.commit()

    uow = SQLAlchemyUnitOfWork(session)
    auth = AllowAllAuthorization()
    policy = ApprovalPolicy()
    idem = SQLAlchemyIdempotencyRepository(session)
    audit = SQLAlchemyAuditRepository(session)
    outbox = SQLAlchemyOutboxRepository(session)

    triage = TriageCaseReliabilityBoundary(uow=uow, handler=TriageCaseHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    start_analysis = StartAnalysisReliabilityBoundary(uow=uow, handler=StartAnalysisHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    create_evidence = CreateEvidenceReliabilityBoundary(uow=uow, handler=CreateEvidenceHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    add_finding = AddAnalysisFindingReliabilityBoundary(uow=uow, handler=AddAnalysisFindingHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    submit_options = SubmitOptionsReliabilityBoundary(uow=uow, handler=SubmitOptionsHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    await_decision = AwaitDecisionReliabilityBoundary(uow=uow, handler=AwaitDecisionHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    make_decision = MakeDecisionReliabilityBoundary(uow=uow, handler=MakeDecisionHandler(uow, auth, policy), option_repository=uow.decision_options, idempotency=idem, audit=audit, outbox=outbox)
    approve = ApproveDecisionReliabilityBoundary(uow=uow, handler=ApproveDecisionHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    create_action = CreateActionReliabilityBoundary(uow=uow, handler=CreateActionHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    start_action = StartActionReliabilityBoundary(uow=uow, handler=StartActionHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    complete_execution = CompleteActionExecutionReliabilityBoundary(uow=uow, handler=CompleteActionExecutionHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    create_expected = CreateExpectedOutcomeReliabilityBoundary(uow=uow, handler=CreateExpectedOutcomeHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    record_actual = RecordActualOutcomeReliabilityBoundary(uow=uow, handler=RecordActualOutcomeHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)
    verify = VerifyOutcomeReliabilityBoundary(uow=uow, handler=VerifyOutcomeHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox)

    triage.execute(TriageCaseCommand(tenant_id, case_id, actor_id), idempotency_key="slice-triage")
    start_analysis.execute(StartAnalysisCommand(tenant_id, case_id, actor_id), idempotency_key="slice-analysis")

    evidence = create_evidence.execute(CreateEvidenceCommand(
        tenant_id=tenant_id, case_id=case_id, actor_id=actor_id, evidence_id=uuid4(),
        source="PSA", metric="gross_margin_percent", value="8.5", unit="percent",
        period="2026-09", captured_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        confidence=0.99, snapshot="project-alpha:margin",
    ), idempotency_key="slice-evidence")

    add_finding.execute(AddAnalysisFindingCommand(
        tenant_id=tenant_id, case_id=case_id, actor_id=actor_id, finding_id=uuid4(),
        kind=AnalysisKind.INFERENCE, statement="Current margin is below target and requires intervention.",
        confidence=0.9, evidence_ids=(evidence.id,),
    ), idempotency_key="slice-finding")

    option_ids = (uuid4(), uuid4())
    submit_options.execute(SubmitOptionsCommand(
        tenant_id=tenant_id, case_id=case_id, actor_id=actor_id,
        options=((option_ids[0], "Reduce non-critical scope"), (option_ids[1], "Renegotiate delivery cost")),
    ), idempotency_key="slice-options")
    await_decision.execute(AwaitDecisionCommand(tenant_id, case_id, actor_id), idempotency_key="slice-await")

    decision = make_decision.execute(MakeDecisionCommand(
        tenant_id=tenant_id, case_id=case_id, decision_id=uuid4(),
        option_ids=(option_ids[0],), rationale="Reduce avoidable delivery cost while protecting critical scope.", actor_id=actor_id,
    ), idempotency_key="slice-decision")
    assert decision.status.value == "AWAITING_APPROVAL"

    approve.execute(ApproveDecisionCommand(tenant_id, case_id, decision.id, actor_id), idempotency_key="slice-approval")

    action = create_action.execute(CreateActionCommand(
        tenant_id=tenant_id, case_id=case_id, decision_id=decision.id, actor_id=actor_id,
        action_type="INTERNAL_SCOPE_ADJUSTMENT", parameters="remove-non-critical-scope", action_id=uuid4(),
    ), idempotency_key="slice-action")
    execution = start_action.execute(StartActionCommand(tenant_id=tenant_id, action_id=action.id, actor_id=actor_id), idempotency_key="slice-start")
    complete_execution.execute(CompleteActionExecutionCommand(
        tenant_id=tenant_id, execution_id=execution.id, actor_id=actor_id, outcome=ActionExecutionStatus.SUCCEEDED,
    ), idempotency_key="slice-complete")

    expected = create_expected.execute(CreateExpectedOutcomeCommand(
        tenant_id=tenant_id, case_id=case_id, actor_id=actor_id, outcome_id=uuid4(),
        metric="gross_margin_percent", operator="GTE", target=10,
    ), idempotency_key="slice-expected")
    actual = record_actual.execute(RecordActualOutcomeCommand(
        tenant_id=tenant_id, case_id=case_id, actor_id=actor_id, outcome_id=uuid4(),
        expected_outcome_id=expected.id, observed_value=11,
    ), idempotency_key="slice-actual")
    verification = verify.execute(VerifyOutcomeCommand(
        tenant_id=tenant_id, case_id=case_id, actor_id=actor_id,
        verification_id=uuid4(), actual_outcome_id=actual.id,
    ), idempotency_key="slice-verify")

    assert verification.status.value == "PASSED"
    persisted = session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case_id))
    assert persisted is not None
    assert persisted.status == "CLOSED"
    assert persisted.version == 10
