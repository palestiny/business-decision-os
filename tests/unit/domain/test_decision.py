from uuid import uuid4

import pytest

from decision_os.domain.decision import (
    Decision,
    DecisionOption,
    DecisionStatus,
    InvalidDecision,
)


def test_decision_requires_at_least_one_option() -> None:
    with pytest.raises(InvalidDecision):
        Decision.make(
            id=uuid4(),
            case_id=uuid4(),
            available_options=(),
            selected_option_ids=(),
            rationale="Valid rationale",
            decided_by=uuid4(),
            approval_required=False,
        )


def test_decision_cannot_select_option_from_another_case() -> None:
    case_id = uuid4()
    option = DecisionOption(id=uuid4(), case_id=uuid4(), title="Other case")

    with pytest.raises(InvalidDecision):
        Decision.make(
            id=uuid4(),
            case_id=case_id,
            available_options=(option,),
            selected_option_ids=(option.id,),
            rationale="Valid rationale",
            decided_by=uuid4(),
            approval_required=False,
        )


def test_decision_with_required_approval_is_not_approved() -> None:
    option = DecisionOption(id=uuid4(), case_id=uuid4(), title="Reallocate resources")

    decision = Decision.make(
        id=uuid4(),
        case_id=option.case_id,
        available_options=(option,),
        selected_option_ids=(option.id,),
        rationale="Protect project margin",
        decided_by=uuid4(),
        approval_required=True,
    )

    assert decision.status is DecisionStatus.AWAITING_APPROVAL


def test_approval_moves_decision_to_approved() -> None:
    option = DecisionOption(id=uuid4(), case_id=uuid4(), title="Bill change request")

    decision = Decision.make(
        id=uuid4(),
        case_id=option.case_id,
        available_options=(option,),
        selected_option_ids=(option.id,),
        rationale="Recover scope leakage",
        decided_by=uuid4(),
        approval_required=True,
    )

    decision.approve()

    assert decision.status is DecisionStatus.APPROVED


def test_decision_without_required_approval_is_immediately_approved() -> None:
    option = DecisionOption(id=uuid4(), case_id=uuid4(), title="Reallocate resources")

    decision = Decision.make(
        id=uuid4(),
        case_id=option.case_id,
        available_options=(option,),
        selected_option_ids=(option.id,),
        rationale="Reduce labor variance",
        decided_by=uuid4(),
        approval_required=False,
    )

    assert decision.status is DecisionStatus.APPROVED
