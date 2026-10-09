from datetime import datetime, timezone
from uuid import uuid4

from decision_os.domain.analysis import AnalysisFinding, AnalysisKind
from decision_os.domain.decision import Decision, DecisionOption
from decision_os.domain.decision_case import CaseStatus, DecisionCase
from decision_os.domain.evidence import Evidence


def test_resource_capacity_risk_reuses_existing_decision_core() -> None:
    tenant_id = uuid4()
    case = DecisionCase.create(
        id=uuid4(),
        tenant_id=tenant_id,
        case_type="RESOURCE_CAPACITY_RISK",
        title="Critical delivery capacity gap",
    )

    case.triage()
    case.start_analysis()

    demand = Evidence.create(
        id=uuid4(),
        case_id=case.id,
        source="PSA",
        metric="required_capacity_hours",
        value="240",
        unit="hours",
        period="2026-10",
        captured_at=datetime.now(timezone.utc),
        confidence=0.99,
        snapshot="project-portfolio:required-capacity",
    )
    available = Evidence.create(
        id=uuid4(),
        case_id=case.id,
        source="RESOURCE_SYSTEM",
        metric="available_capacity_hours",
        value="180",
        unit="hours",
        period="2026-10",
        captured_at=datetime.now(timezone.utc),
        confidence=0.98,
        snapshot="resource-pool:available-capacity",
    )

    finding = AnalysisFinding.create(
        id=uuid4(),
        case_id=case.id,
        kind=AnalysisKind.INFERENCE,
        statement="Demand exceeds available capacity by 60 hours.",
        confidence=0.95,
        evidence_ids=(demand.id, available.id),
    )

    assert finding.case_id == case.id
    assert finding.kind is AnalysisKind.INFERENCE

    case.submit_options()
    case.await_decision()

    options = (
        DecisionOption(uuid4(), case.id, "Reallocate internal capacity"),
        DecisionOption(uuid4(), case.id, "Defer lower-priority delivery work"),
    )
    decision = Decision.make(
        id=uuid4(),
        case_id=case.id,
        available_options=options,
        selected_option_ids=(options[0].id,),
        rationale="Reallocate capacity to protect the highest-priority delivery commitments.",
        decided_by=uuid4(),
        approval_required=True,
    )

    case.record_decision(approval_required=decision.approval_required)

    assert case.status is CaseStatus.AWAITING_APPROVAL
    assert len(options) == 2
    assert decision.selected_option_ids == (options[0].id,)


def test_resource_capacity_risk_evidence_remains_immutable() -> None:
    evidence = Evidence.create(
        id=uuid4(),
        case_id=uuid4(),
        source="RESOURCE_SYSTEM",
        metric="available_capacity_hours",
        value="180",
        unit="hours",
        period="2026-10",
        captured_at=datetime.now(timezone.utc),
        confidence=1.0,
        snapshot="resource-pool:available-capacity",
    )

    assert evidence.metric == "available_capacity_hours"
    assert evidence.value == "180"

    try:
        evidence.value = "200"
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("Evidence must remain immutable")
