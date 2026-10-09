from datetime import datetime, timezone
from uuid import uuid4

import pytest

from decision_os.domain.evidence import Evidence, InvalidEvidence
from decision_os.domain.analysis import AnalysisFinding, AnalysisKind, InvalidAnalysis


def test_evidence_is_immutable_and_requires_source_and_metric():
    evidence = Evidence.create(
        id=uuid4(),
        case_id=uuid4(),
        source="PSA",
        metric="gross_margin_percent",
        value="12.5",
        unit="percent",
        period="2026-09",
        captured_at=datetime.now(timezone.utc),
        confidence=0.95,
        snapshot="project-123:margin",
    )
    assert evidence.metric == "gross_margin_percent"
    with pytest.raises((AttributeError, TypeError)):
        evidence.metric = "changed"


@pytest.mark.parametrize(
    "confidence",
    [-0.1, 1.1],
)
def test_evidence_rejects_invalid_confidence(confidence):
    with pytest.raises(InvalidEvidence):
        Evidence.create(
            id=uuid4(),
            case_id=uuid4(),
            source="PSA",
            metric="gross_margin_percent",
            value="12.5",
            unit="percent",
            period="2026-09",
            captured_at=datetime.now(timezone.utc),
            confidence=confidence,
            snapshot="project-123:margin",
        )


def test_analysis_finding_requires_evidence_and_explicit_kind():
    evidence_id = uuid4()
    finding = AnalysisFinding.create(
        id=uuid4(),
        case_id=uuid4(),
        kind=AnalysisKind.INFERENCE,
        statement="Margin deterioration is driven by cost growth.",
        confidence=0.8,
        evidence_ids=(evidence_id,),
    )
    assert finding.kind is AnalysisKind.INFERENCE
    assert finding.evidence_ids == (evidence_id,)


def test_analysis_finding_rejects_missing_evidence():
    with pytest.raises(InvalidAnalysis):
        AnalysisFinding.create(
            id=uuid4(),
            case_id=uuid4(),
            kind=AnalysisKind.HYPOTHESIS,
            statement="Costs may continue to rise.",
            confidence=0.5,
            evidence_ids=(),
        )
