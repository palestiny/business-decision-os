from uuid import uuid4

from decision_os.application.commands.approve_decision import (
    ApproveDecisionCommand,
    ApproveDecisionHandler,
)
from decision_os.application.commands.make_decision import (
    MakeDecisionCommand,
    MakeDecisionHandler,
)
from decision_os.application.commands.reject_decision import (
    RejectDecisionCommand,
    RejectDecisionHandler,
)
from decision_os.application.commands.triage_case import (
    TriageCaseCommand,
    TriageCaseHandler,
)
from decision_os.domain.decision import Decision, DecisionOption, DecisionStatus
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

    def get(self, decision_id, tenant_id):
        return self.items.get(decision_id)

    def add(self, decision):
        self.items[decision.id] = decision

    def save(self, decision, tenant_id):
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


def make_case():
    return DecisionCase.create(
        id=uuid4(),
        tenant_id=uuid4(),
        case_type="PROJECT_MARGIN_RISK",
        title="Margin risk",
    )


def move_to_awaiting_decision(case):
    case.triage()
    case.start_analysis()
    case.submit_options()
    case.await_decision()


def test_triage_loads_by_tenant_and_commits():
    case = make_case()
    uow = Uow(case)

    result = TriageCaseHandler(uow).handle(
        TriageCaseCommand(tenant_id=case.tenant_id, case_id=case.id)
    )

    assert result.status is CaseStatus.TRIAGED
    assert uow.commits == 1


def test_make_decision_preserves_approval_boundary_and_case_state():
    case = make_case()
    move_to_awaiting_decision(case)
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
    assert case.status is CaseStatus.AWAITING_APPROVAL
    assert uow.commits == 1


def test_make_decision_without_approval_moves_case_to_approved():
    case = make_case()
    move_to_awaiting_decision(case)
    option = DecisionOption(uuid4(), case.id, "Reduce scope")
    uow = Uow(case)

    decision = MakeDecisionHandler(uow).handle(
        MakeDecisionCommand(
            tenant_id=case.tenant_id,
            case_id=case.id,
            decision_id=uuid4(),
            option_ids=(option.id,),
            rationale="Protect margin",
            actor_id=uuid4(),
            approval_required=False,
        ),
        case_options=(option,),
    )

    assert decision.status is DecisionStatus.APPROVED
    assert case.status is CaseStatus.APPROVED


def test_approve_decision_loads_and_persists_by_tenant():
    case = make_case()
    move_to_awaiting_decision(case)
    option = DecisionOption(uuid4(), case.id, "Bill change request")
    decision = Decision.make(
        id=uuid4(),
        case_id=case.id,
        available_options=(option,),
        selected_option_ids=(option.id,),
        rationale="Recover leakage",
        decided_by=uuid4(),
        approval_required=True,
    )
    uow = Uow(case)
    uow.decisions.add(decision)
    case.record_decision(approval_required=True)

    result = ApproveDecisionHandler(uow).handle(
        ApproveDecisionCommand(
            tenant_id=case.tenant_id,
            case_id=case.id,
            decision_id=decision.id,
        )
    )

    assert result.status is DecisionStatus.APPROVED
    assert uow.decisions.items[decision.id].status is DecisionStatus.APPROVED
    assert case.status is CaseStatus.APPROVED
    assert uow.commits == 1


def test_reject_decision_persists_rejection_and_case_state():
    case = make_case()
    move_to_awaiting_decision(case)
    option = DecisionOption(uuid4(), case.id, "Reduce scope")
    decision = Decision.make(
        id=uuid4(),
        case_id=case.id,
        available_options=(option,),
        selected_option_ids=(option.id,),
        rationale="Reject unprofitable scope",
        decided_by=uuid4(),
        approval_required=True,
    )
    uow = Uow(case)
    uow.decisions.add(decision)
    case.record_decision(approval_required=True)

    result = RejectDecisionHandler(uow).handle(
        RejectDecisionCommand(
            tenant_id=case.tenant_id,
            case_id=case.id,
            decision_id=decision.id,
        )
    )

    assert result.status is DecisionStatus.REJECTED
    assert uow.decisions.items[decision.id].status is DecisionStatus.REJECTED
    assert case.status is CaseStatus.REJECTED
    assert uow.commits == 1
