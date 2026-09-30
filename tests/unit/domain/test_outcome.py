from uuid import uuid4

import pytest

from decision_os.domain.decision_case import CaseStatus, DecisionCase, InvalidCaseTransition
from decision_os.domain.outcome import ActualOutcome, ExpectedOutcome, OutcomeStatus, Verification, VerificationStatus


def test_expected_outcome_rejects_invalid_operator():
    with pytest.raises(ValueError):
        ExpectedOutcome.create(id=uuid4(), case_id=uuid4(), metric="margin", operator="NE", target=10)


@pytest.mark.parametrize(
    ("operator", "observed", "expected_status"),
    [
        ("GT", 11, VerificationStatus.PASSED),
        ("GTE", 10, VerificationStatus.PASSED),
        ("EQ", 10, VerificationStatus.PASSED),
        ("LTE", 10, VerificationStatus.PASSED),
        ("LT", 9, VerificationStatus.PASSED),
        ("GT", 10, VerificationStatus.FAILED),
    ],
)
def test_verification_is_deterministic(operator, observed, expected_status):
    case_id = uuid4()
    expected = ExpectedOutcome.create(id=uuid4(), case_id=case_id, metric="margin", operator=operator, target=10)
    actual = ActualOutcome(id=uuid4(), case_id=case_id, expected_outcome_id=expected.id, observed_value=observed)
    verification = Verification(id=uuid4(), case_id=case_id, actual_outcome_id=actual.id)

    assert verification.verify(expected=expected, actual=actual) is expected_status


def test_unknown_actual_outcome_is_inconclusive():
    case_id = uuid4()
    expected = ExpectedOutcome.create(id=uuid4(), case_id=case_id, metric="margin", operator="GTE", target=10)
    actual = ActualOutcome(id=uuid4(), case_id=case_id, expected_outcome_id=expected.id, observed_value=0)
    actual.mark_unknown()
    verification = Verification(id=uuid4(), case_id=case_id, actual_outcome_id=actual.id)

    assert verification.verify(expected=expected, actual=actual) is VerificationStatus.INCONCLUSIVE


def test_case_can_progress_from_outcome_pending_to_closed_after_verification():
    case = DecisionCase(uuid4(), uuid4(), "PROJECT_MARGIN_RISK", "Margin risk", CaseStatus.OUTCOME_PENDING, 8)

    case.start_verification()
    assert case.status is CaseStatus.VERIFYING
    assert case.version == 9

    case.close()
    assert case.status is CaseStatus.CLOSED
    assert case.version == 10


def test_case_cannot_close_before_verification():
    case = DecisionCase(uuid4(), uuid4(), "PROJECT_MARGIN_RISK", "Margin risk", CaseStatus.OUTCOME_PENDING, 8)
    with pytest.raises(InvalidCaseTransition):
        case.close()
