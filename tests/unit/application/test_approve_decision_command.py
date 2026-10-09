from datetime import datetime, timezone
from uuid import uuid4

import pytest

from decision_os.application.commands.approve_decision import (
    ApproveDecisionCommand,
    ApproveDecisionHandler,
)
from decision_os.application.ports.authority import (
    Permission,
    SeparationOfDutiesViolation,
)
from decision_os.domain.decision import Decision, DecisionOption, DecisionStatus
from decision_os.domain.decision_case import CaseStatus, DecisionCase


class Authorization:
    def __init__(self):
        self.calls = []

    def require(self, **kwargs):
        self.calls.append(kwargs)


class Cases:
    def __init__(self, case):
        self.case = case
        self.saved = []

    def get(self, case_id, tenant_id):
        if case_id == self.case.id and tenant_id == self.case.tenant_id:
            return self.case
        return None

    def save(self, case, **kwargs):
        self.saved.append(case)


class Decisions:
    def __init__(self, decision):
        self.decision = decision
        self.saved = []

    def get(self, decision_id, tenant_id):
        if decision_id == self.decision.id:
            return self.decision
        return None

    def save(self, decision, tenant_id):
        self.saved.append(decision)


class Uow:
    def __init__(self, case, decision):
        self.decision_cases = Cases(case)
        self.decisions = Decisions(decision)


def make_scenario(*, creator_id=None, decision_maker_id=None):
    tenant_id = uuid4()
    creator_id = creator_id if creator_id is not None else uuid4()
    decision_maker_id = decision_maker_id if decision_maker_id is not None else uuid4()
    case_id, decision_id, option_id = uuid4(), uuid4(), uuid4()
    case = DecisionCase(
        id=case_id,
        tenant_id=tenant_id,
        case_type="PROJECT_MARGIN_RISK",
        title="Margin risk",
        created_by=creator_id,
        status=CaseStatus.AWAITING_APPROVAL,
        version=2,
    )
    option = DecisionOption(id=option_id, case_id=case_id, title="Protect margin")
    decision = Decision.make(
        id=decision_id,
        case_id=case_id,
        available_options=(option,),
        selected_option_ids=(option_id,),
        rationale="Protect delivery margin.",
        decided_by=decision_maker_id,
        approval_required=True,
    )
    return tenant_id, case, decision


def invoke(case, decision, actor_id):
    auth = Authorization()
    uow = Uow(case, decision)
    handler = ApproveDecisionHandler(uow, auth)
    result = handler.handle(
        ApproveDecisionCommand(
            tenant_id=case.tenant_id,
            case_id=case.id,
            decision_id=decision.id,
            actor_id=actor_id,
        )
    )
    return result, auth, uow


@pytest.mark.parametrize("identity_field", ["creator", "decision_maker"])
def test_approval_denies_creator_and_decision_maker_even_when_authorized(identity_field):
    tenant_id = uuid4()
    creator_id, decision_maker_id = uuid4(), uuid4()
    case_tenant, case, decision = make_scenario(
        creator_id=creator_id,
        decision_maker_id=decision_maker_id,
    )
    assert case_tenant == case.tenant_id
    actor_id = creator_id if identity_field == "creator" else decision_maker_id
    auth = Authorization()
    uow = Uow(case, decision)
    handler = ApproveDecisionHandler(uow, auth)

    with pytest.raises(SeparationOfDutiesViolation):
        handler.handle(ApproveDecisionCommand(
            tenant_id=case.tenant_id,
            case_id=case.id,
            decision_id=decision.id,
            actor_id=actor_id,
        ))

    assert auth.calls[0]["permission"] is Permission.APPROVE_DECISION
    assert decision.status is DecisionStatus.AWAITING_APPROVAL
    assert decision.approved_by is None
    assert uow.decisions.saved == []


def test_approval_fails_closed_for_legacy_case_without_creator_attribution():
    _, case, decision = make_scenario()
    case.created_by = None
    auth = Authorization()
    uow = Uow(case, decision)

    with pytest.raises(SeparationOfDutiesViolation, match="creator attribution"):
        ApproveDecisionHandler(uow, auth).handle(ApproveDecisionCommand(
            tenant_id=case.tenant_id,
            case_id=case.id,
            decision_id=decision.id,
            actor_id=uuid4(),
        ))

    assert decision.status is DecisionStatus.AWAITING_APPROVAL
    assert uow.decisions.saved == []


def test_distinct_approver_is_persisted_on_domain_decision():
    _, case, decision = make_scenario()
    approver_id = uuid4()
    result, auth, uow = invoke(case, decision, approver_id)

    assert result.status is DecisionStatus.APPROVED
    assert result.approved_by == approver_id
    assert result.approved_at is not None
    assert result.approved_at.tzinfo is not None
    assert auth.calls[0]["permission"] is Permission.APPROVE_DECISION
    assert uow.decisions.saved == [decision]
    assert uow.decision_cases.saved == [case]
