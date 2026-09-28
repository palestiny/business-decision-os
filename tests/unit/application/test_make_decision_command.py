from uuid import uuid4

import pytest

from decision_os.application.commands.make_decision import MakeDecisionCommand, MakeDecisionHandler
from decision_os.application.ports.authority import (
    ApprovalDecision,
    AuthorizationDenied,
    Permission,
    PolicyEvaluationUnavailable,
)
from decision_os.domain.decision import DecisionOption, DecisionStatus
from decision_os.domain.decision_case import CaseStatus, DecisionCase


class Cases:
    def __init__(self, case):
        self.case = case

    def get(self, case_id, tenant_id):
        return self.case if case_id == self.case.id and tenant_id == self.case.tenant_id else None

    def save(self, case):
        self.case = case


class Decisions:
    def __init__(self):
        self.items = []

    def add(self, decision):
        self.items.append(decision)


class Uow:
    def __init__(self, case):
        self.decision_cases = Cases(case)
        self.decisions = Decisions()
        self.commits = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        raise AssertionError("handler must not own rollback")


class Authorization:
    def __init__(self):
        self.calls = []

    def require(self, **kwargs):
        self.calls.append(kwargs)


class Policy:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def evaluate(self, **kwargs):
        if self.error:
            raise self.error
        return self.result


def test_make_decision_policy_failure_is_fail_closed():
    tenant_id, case_id, actor_id = uuid4(), uuid4(), uuid4()
    option_id = uuid4()
    case = DecisionCase(
        id=case_id,
        tenant_id=tenant_id,
        case_type="PROJECT_MARGIN_RISK",
        title="Margin risk",
        status=CaseStatus.AWAITING_DECISION,
        version=4,
    )
    uow = Uow(case)
    handler = MakeDecisionHandler(
        uow=uow,
        authorization=Authorization(),
        policy_evaluator=Policy(error=PolicyEvaluationUnavailable("policy unavailable")),
    )

    with pytest.raises(PolicyEvaluationUnavailable):
        handler.handle(
            MakeDecisionCommand(
                tenant_id=tenant_id,
                case_id=case_id,
                decision_id=uuid4(),
                option_ids=(option_id,),
                rationale="Protect margin.",
                actor_id=actor_id,
            ),
            case_options=(DecisionOption(id=option_id, case_id=case_id, title="Protect"),),
        )

    assert uow.decisions.items == []
    assert uow.decision_cases.case.status is CaseStatus.AWAITING_DECISION
    assert uow.decision_cases.case.version == 4
    assert uow.commits == 0


def test_make_decision_uses_policy_authority_snapshot():
    tenant_id, case_id, actor_id = uuid4(), uuid4(), uuid4()
    option_id, policy_id = uuid4(), uuid4()
    case = DecisionCase(
        id=case_id,
        tenant_id=tenant_id,
        case_type="PROJECT_MARGIN_RISK",
        title="Margin risk",
        status=CaseStatus.AWAITING_DECISION,
        version=2,
    )
    policy = Policy(result=ApprovalDecision(required=True, policy_ids=(policy_id,)))
    uow = Uow(case)
    handler = MakeDecisionHandler(
        uow=uow,
        authorization=Authorization(),
        policy_evaluator=policy,
    )

    decision = handler.handle(
        MakeDecisionCommand(
            tenant_id=tenant_id,
            case_id=case_id,
            decision_id=uuid4(),
            option_ids=(option_id,),
            rationale="Protect margin.",
            actor_id=actor_id,
        ),
        case_options=(DecisionOption(id=option_id, case_id=case_id, title="Protect"),),
    )

    assert decision.status is DecisionStatus.AWAITING_APPROVAL
    assert decision.approval_required is True
    assert decision.policy_ids == (policy_id,)
    assert case.status is CaseStatus.AWAITING_APPROVAL
    assert case.version == 3
    assert uow.commits == 0
