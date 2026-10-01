from datetime import datetime, timezone
from uuid import uuid4

import pytest

from decision_os.domain.analysis import AnalysisFinding, AnalysisKind
from decision_os.domain.decision import Decision, DecisionOption, DecisionStatus
from decision_os.domain.decision_case import CaseStatus, DecisionCase
from decision_os.domain.evidence import Evidence


def test_revenue_billing_leakage_reuses_existing_decision_core():
    tenant_id = uuid4()
    case_id = uuid4()
    actor_id = uuid4()

    case = DecisionCase.create(
        id=case_id,
        tenant_id=tenant_id,
        case_type="REVENUE_BILLING_LEAKAGE",
        title="October billing leakage",
    )
    case.triage()
    case.start_analysis()

    captured_at = datetime.now(timezone.utc)
    contracted = Evidence.create(
        id=uuid4(),
        case_id=case_id,
        source="CRM",
        metric="contracted_revenue",
        value="100000",
        unit="EGP",
        period="2026-10",
        captured_at=captured_at,
        confidence=0.99,
        snapshot="billing-october:contracted",
    )
    delivered = Evidence.create(
        id=uuid4(),
        case_id=case_id,
        source="DELIVERY_SYSTEM",
        metric="delivered_revenue",
        value="90000",
        unit="EGP",
        period="2026-10",
        captured_at=captured_at,
        confidence=0.98,
        snapshot="billing-october:delivered",
    )
    billed = Evidence.create(
        id=uuid4(),
        case_id=case_id,
        source="BILLING_SYSTEM",
        metric="billed_revenue",
        value="75000",
        unit="EGP",
        period="2026-10",
        captured_at=captured_at,
        confidence=0.99,
        snapshot="billing-october:billed",
    )

    finding = AnalysisFinding.create(
        id=uuid4(),
        case_id=case_id,
        kind=AnalysisKind.INFERENCE,
        statement="Delivered value exceeds billed value by 15000 EGP.",
        confidence=0.95,
        evidence_ids=(delivered.id, billed.id),
    )

    assert case.status is CaseStatus.ANALYZING
    assert finding.kind is AnalysisKind.INFERENCE
    assert set(finding.evidence_ids) == {delivered.id, billed.id}
    assert contracted.value == "100000"

    case.submit_options()
    options = (
        DecisionOption.create(uuid4(), case_id, "Issue corrective invoice"),
        DecisionOption.create(uuid4(), case_id, "Escalate contract and billing review"),
    )
    case.await_decision()

    decision = Decision.make(
        id=uuid4(),
        case_id=case_id,
        option_ids=(options[0].id,),
        rationale="Recover delivered value that has not been billed.",
        decided_by=actor_id,
        options=options,
        approval_required=True,
    )

    assert decision.status is DecisionStatus.AWAITING_APPROVAL


def test_revenue_billing_leakage_evidence_remains_immutable():
    evidence = Evidence.create(
        id=uuid4(),
        case_id=uuid4(),
        source="BILLING_SYSTEM",
        metric="billed_revenue",
        value="75000",
        unit="EGP",
        period="2026-10",
        captured_at=datetime.now(timezone.utc),
        confidence=0.99,
        snapshot="billing-october:billed",
    )

    with pytest.raises((AttributeError, TypeError)):
        evidence.value = "90000"
