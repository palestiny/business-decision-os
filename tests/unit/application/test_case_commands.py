from uuid import uuid4

import pytest

from decision_os.application.commands.approve_decision import (
    ApproveDecisionCommand,
    ApproveDecisionHandler,
)
from decision_os.application.commands.make_decision import (
    MakeDecisionCommand,
    MakeDecisionHandler,
)
from decision_os.application.commands.triage_case import (
    TriageCaseCommand,
    TriageCaseHandler,
)
from decision_os.domain.decision import DecisionOption, DecisionStatus
from decision_os.domain.decision_case import CaseStatus, DecisionCase


class Cases:
    def __init__(self):
        self.items = {}

    def get(self, case_id, tenant_id):
        return self.items.get((tenant_id, case_id))

    def add(self, case):
        self.items[(case.tenant_id, case.id)] = case

    def save(self, case):
        self.items[(case.tenant_id, case.id)] = case


class Decisions:
    def __init__(self):
        self.items = {}

    def add(self, decision):
        self.items[decision.id] = decision

    def get(self, decision_id, tenant_id):
        return self.items.get(decision_id)

    def save(self, decision):
        self.items[decision.id] = decision


class Uow:
    def __init__(self, case):
        self.decision_cases = Cases()
        self.decisions = Decisions()
        self.decision_cases.add(case)
        self.commits = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


def test_triage_loads_by_tenant_and_commits():
    case = DecisionCase.create(
        id=uuid4(), tenant_id=uuid4(), case_type="PROJECT_MARGIN_RISK", title="Margin risk"
    )
    uow = Uow(case)
    result = TriageCaseHandler(uow).handle(
        TriageCaseCommand(tenant_id=case.tenant_id, case_id=case.id)
    )
    assert result.status is CaseStatus.TRIAGED
    assert uow.commits == 1


def test_make_decision_preserves_approval_boundary():
    case = DecisionCase.create(
        id=uuid4(), tenant_id=uuid4(), case_type="PROJECT_MARGIN_RISK", title="Margin risk"
    )
    option = DecisionOption(uuid4(), case.id, "Reallocate resources")
    uow = Uow(case)
    decision = MakeDecisionHandler(uow).handle(
        MakeDecisionCommand(
            tenant_id=case.tenant_id,
            case_id=case.id,
            decision_id=uuid4(),
            option_ids=(option.id,),
            rationale="Protect margin",
            actor_id=uuid4(),
            approval_required=True,
        ),
        case_options=(option,),
    )
    assert decision.status is DecisionStatus.AWAITING_APPROVAL


def test_approve_decision_requires_existing_case():
    case = DecisionCase.create(
        id=uuid4(), tenant_id=uuid4(), case_type="PROJECT_MARGIN_RISK", title="Margin risk"
    )
    option = DecisionOption(uuid4(), case.id, "Bill change request")
    uow = Uow(case)
    from decision_os.domain.decision import Decision
    decision = Decision.make(
        id=uuid4(), case_id=case.id, available_options=(option,),
        selected_option_ids=(option.id,), rationale="Recover leakage",
        decided_by=uuid4(), approval_required=True,
    )
    result = ApproveDecisionHandler(uow).handle(
        ApproveDecisionCommand(case.tenant_id, case.id, decision)
    )
    assert result.status is DecisionStatus.APPROVED
