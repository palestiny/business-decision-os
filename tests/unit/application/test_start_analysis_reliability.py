from uuid import uuid4

from decision_os.application.start_analysis_reliability import StartAnalysisReliabilityBoundary
from decision_os.domain.decision_case import CaseStatus, DecisionCase


def test_start_analysis_idempotency_response_preserves_case_creator_attribution():
    creator_id = uuid4()
    case = DecisionCase.create(
        id=uuid4(),
        tenant_id=uuid4(),
        case_type="PROJECT_MARGIN_RISK",
        title="Analysis creator replay",
        created_by=creator_id,
    )
    case.triage()
    case.start_analysis()

    restored = StartAnalysisReliabilityBoundary._deserialize(
        StartAnalysisReliabilityBoundary._serialize(case)
    )

    assert restored.id == case.id
    assert restored.created_by == creator_id
    assert restored.status is CaseStatus.ANALYZING
    assert restored.version == 2
