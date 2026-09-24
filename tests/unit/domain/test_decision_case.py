from uuid import uuid4

import pytest

from decision_os.domain.decision_case import (
    CaseStatus,
    DecisionCase,
    InvalidCaseTransition,
)


def make_case() -> DecisionCase:
    return DecisionCase.create(
        id=uuid4(),
        tenant_id=uuid4(),
        case_type="PROJECT_MARGIN_RISK",
        title="Project margin forecast dropped below threshold",
    )


def test_new_case_starts_detected() -> None:
    case = make_case()
    assert case.status is CaseStatus.DETECTED
    assert case.version == 0


def test_valid_lifecycle_transitions_increment_version() -> None:
    case = make_case()

    case.triage()
    case.start_analysis()
    case.submit_options()
    case.await_decision()

    assert case.status is CaseStatus.AWAITING_DECISION
    assert case.version == 4


def test_invalid_transition_is_rejected() -> None:
    case = make_case()

    with pytest.raises(InvalidCaseTransition):
        case.start_analysis()


def test_closed_case_cannot_be_mutated() -> None:
    case = make_case()
    case.status = CaseStatus.CLOSED

    with pytest.raises(InvalidCaseTransition):
        case.triage()


def test_empty_case_type_is_rejected() -> None:
    with pytest.raises(ValueError):
        make_invalid_case(case_type="")


def make_invalid_case(*, case_type: str) -> DecisionCase:
    return DecisionCase.create(
        id=uuid4(),
        tenant_id=uuid4(),
        case_type=case_type,
        title="Valid title",
    )
