from uuid import uuid4

from decision_os.application.commands.approve_decision import ApproveDecisionCommand, ApproveDecisionHandler
from decision_os.application.commands.create_decision_case import CreateDecisionCaseCommand, CreateDecisionCaseHandler
from decision_os.application.commands.make_decision import MakeDecisionCommand, MakeDecisionHandler
from decision_os.application.commands.reject_decision import RejectDecisionCommand, RejectDecisionHandler
from decision_os.application.commands.triage_case import TriageCaseCommand, TriageCaseHandler
from decision_os.application.ports.authority import ApprovalDecision, Permission
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


class Authorization:
    def __init__(self):
        self.calls = []

    def require(self, **kwargs):
        self.calls.append(kwargs)


class PolicyEvaluator:
    def __init__(self, required):
        self.required = required
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return ApprovalDecision(required=self.required)


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
        id=uuid4(), tenant_id=uuid4(), case_type="PROJECT_MARGIN_RISK", title="Margin risk"
    )


def move_to_awaiting_decision(case):
    case.triage()
    case.start_analysis()
    case.submit_options()
    case.await_decision()


def test_create_case_requires_authority_and_commits():
    tenant_id = uuid4()
    actor_id = uuid4()
    uow = Uow(make_case())
    authorization = Authorization()
    result = CreateDecisionCaseHandler(uow, authorization).handle(
        CreateDecisionCaseCommand(tenant_id, "PROJECT_MARGIN_RISK", "Margin risk", actor_id)
    )
    assert result.tenant_id == tenant_id
    assert uow.commits == 1
    assert authorization.calls[0] == {
        "actor_id": actor_id, "tenant_id": tenant_id,
        "permission": Permission.CREATE_CASE, "resource_id": result.id,
    }


def test_triage_loads_by_tenant_and_requires_authority():
    case = make_case()
    uow = Uow(case)
    authorization = Authorization()
    actor_id = uuid4()
    result = TriageCaseHandler(uow, authorization).handle(
        TriageCaseCommand(case.tenant_id, case.id, actor_id)
    )
    assert result.status is CaseStatus.TRIAGED
    assert uow.commits == 1


def test_make_decision_uses_policy_for_approval_requirement():
    case = make_case()
    move_to_awaiting_decision(case)
    option = DecisionOption(uuid4(), case.id, "Reallocate resources")
    uow = Uow(case)
    authorization = Authorization()
    policy = PolicyEvaluator(required=True)
    actor_id = uuid4()

    decision = MakeDecisionHandler(uow, authorization, policy).handle(
        MakeDecisionCommand(case.tenant_id, case.id, uuid4(), (option.id,), "Protect margin", actor_id),
        case_options=(option,),
    )

    assert decision.status is DecisionStatus.AWAITING_APPROVAL
    assert case.status is CaseStatus.AWAITING_APPROVAL
    assert authorization.calls[0]["permission"] is Permission.MAKE_DECISION
    assert policy.calls[0]["case_id"] == case.id


def test_make_decision_policy_can_allow_immediate_approval():
    case = make_case()
    move_to_awaiting_decision(case)
    option = DecisionOption(uuid4(), case.id, "Reduce scope")
    uow = Uow(case)
    authorization = Authorization()
    policy = PolicyEvaluator(required=False)

    decision = MakeDecisionHandler(uow, authorization, policy).handle(
        MakeDecisionCommand(case.tenant_id, case.id, uuid4(), (option.id,), "Protect margin", uuid4()),
        case_options=(option,),
    )

    assert decision.status is DecisionStatus.APPROVED
    assert case.status is CaseStatus.APPROVED


def test_approve_decision_requires_authority_and_persists_by_tenant():
    case = make_case()
    move_to_awaiting_decision(case)
    option = DecisionOption(uuid4(), case.id, "Bill change request")
    decision = Decision.make(
        id=uuid4(), case_id=case.id, available_options=(option,), selected_option_ids=(option.id,),
        rationale="Recover leakage", decided_by=uuid4(), approval_required=True,
    )
    uow = Uow(case)
    uow.decisions.add(decision)
    case.record_decision(approval_required=True)
    authorization = Authorization()
    actor_id = uuid4()

    result = ApproveDecisionHandler(uow, authorization).handle(
        ApproveDecisionCommand(case.tenant_id, case.id, decision.id, actor_id)
    )

    assert result.status is DecisionStatus.APPROVED
    assert case.status is CaseStatus.APPROVED
    assert authorization.calls == [{
        "actor_id": actor_id, "tenant_id": case.tenant_id,
        "permission": Permission.APPROVE_DECISION, "resource_id": case.id,
    }]


def test_reject_decision_requires_authority_and_persists_rejection():
    case = make_case()
    move_to_awaiting_decision(case)
    option = DecisionOption(uuid4(), case.id, "Reduce scope")
    decision = Decision.make(
        id=uuid4(), case_id=case.id, available_options=(option,), selected_option_ids=(option.id,),
        rationale="Reject unprofitable scope", decided_by=uuid4(), approval_required=True,
    )
    uow = Uow(case)
    uow.decisions.add(decision)
    case.record_decision(approval_required=True)
    authorization = Authorization()
    actor_id = uuid4()

    result = RejectDecisionHandler(uow, authorization).handle(
        RejectDecisionCommand(case.tenant_id, case.id, decision.id, actor_id)
    )

    assert result.status is DecisionStatus.REJECTED
    assert case.status is CaseStatus.REJECTED
    assert authorization.calls == [{
        "actor_id": actor_id, "tenant_id": case.tenant_id,
        "permission": Permission.REJECT_DECISION, "resource_id": case.id,
    }]
