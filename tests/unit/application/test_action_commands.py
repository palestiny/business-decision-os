from types import SimpleNamespace
from uuid import uuid4

import pytest

from decision_os.application.commands.create_action import CreateActionCommand, CreateActionHandler
from decision_os.application.commands.start_action import StartActionCommand, StartActionHandler
from decision_os.application.ports.authority import Permission
from decision_os.domain.action import Action, ActionExecutionStatus, ActionStatus
from decision_os.domain.decision import Decision, DecisionStatus
from decision_os.domain.decision_case import CaseStatus, DecisionCase


class FakeAuthorization:
    def __init__(self):
        self.calls = []

    def require(self, **kwargs):
        self.calls.append(kwargs)


def approved_context():
    tenant_id = uuid4()
    case = DecisionCase(uuid4(), tenant_id, "PROJECT_MARGIN_RISK", "Margin risk", CaseStatus.APPROVED, 7)
    decision = Decision(
        id=uuid4(), case_id=case.id, selected_option_ids=(uuid4(),),
        rationale="selected", status=DecisionStatus.APPROVED, decided_by=uuid4(),
    )
    return tenant_id, case, decision


def test_create_action_requires_approved_case_and_decision_and_returns_ready():
    tenant_id, case, decision = approved_context()
    auth = FakeAuthorization()
    actions = []

    uow = SimpleNamespace(
        decision_cases=SimpleNamespace(get=lambda *_: case),
        decisions=SimpleNamespace(get=lambda *_: decision),
        actions=SimpleNamespace(add=actions.append),
    )

    result = CreateActionHandler(uow, auth).handle(CreateActionCommand(
        tenant_id=tenant_id, case_id=case.id, decision_id=decision.id,
        actor_id=uuid4(), action_type="UPDATE_BUDGET", parameters="{}",
    ))

    assert result.status is ActionStatus.READY
    assert result.version == 1
    assert actions == [result]
    assert auth.calls[0]["permission"] is Permission.CREATE_ACTION


def test_start_action_creates_first_execution_and_moves_case_to_executing():
    tenant_id, case, decision = approved_context()
    action = Action.create(
        id=uuid4(), tenant_id=tenant_id, case_id=case.id, decision_id=decision.id,
        action_type="UPDATE_BUDGET", parameters="{}",
    )
    action.ready()
    saved = []
    executions = []
    auth = FakeAuthorization()

    uow = SimpleNamespace(
        actions=SimpleNamespace(get=lambda *_: action, save=lambda value, expected_version: saved.append((value, expected_version))),
        decision_cases=SimpleNamespace(get=lambda *_: case, save=lambda value, expected_version=None: saved.append((value, expected_version))),
        action_executions=SimpleNamespace(get_latest_for_action=lambda *_: None, add=executions.append),
    )

    result = StartActionHandler(uow, auth).handle(StartActionCommand(
        tenant_id=tenant_id, action_id=action.id, actor_id=uuid4(),
    ))

    assert result.attempt == 1
    assert result.status is ActionExecutionStatus.RUNNING
    assert action.status is ActionStatus.EXECUTING
    assert case.status is CaseStatus.EXECUTING
    assert saved[0][1] == 1
    assert saved[1][1] == 7
    assert executions == [result]
    assert auth.calls[0]["permission"] is Permission.START_ACTION


def test_start_action_blocks_retry_when_latest_execution_is_unknown():
    tenant_id, case, decision = approved_context()
    action = Action.create(
        id=uuid4(), tenant_id=tenant_id, case_id=case.id, decision_id=decision.id,
        action_type="UPDATE_BUDGET", parameters="{}",
    )
    action.ready()
    latest = SimpleNamespace(status=ActionExecutionStatus.UNKNOWN, attempt=1)
    auth = FakeAuthorization()
    uow = SimpleNamespace(
        actions=SimpleNamespace(get=lambda *_: action),
        decision_cases=SimpleNamespace(get=lambda *_: case),
        action_executions=SimpleNamespace(get_latest_for_action=lambda *_: latest),
    )

    with pytest.raises(ValueError, match="unknown"):
        StartActionHandler(uow, auth).handle(StartActionCommand(
            tenant_id=tenant_id, action_id=action.id, actor_id=uuid4(),
        ))


def test_running_execution_can_complete_successfully_and_moves_case_to_outcome_pending():
    tenant_id, case, decision = approved_context()
    action = Action.create(id=uuid4(), tenant_id=tenant_id, case_id=case.id, decision_id=decision.id, action_type="UPDATE_BUDGET", parameters="{}")
    action.ready()
    action.start_execution()
    execution = __import__("decision_os.domain.action", fromlist=["ActionExecution"]).ActionExecution.request(id=uuid4(), action_id=action.id, attempt=1)
    execution.start()
    auth = FakeAuthorization()
    saved = []
    uow = SimpleNamespace(
        action_executions=SimpleNamespace(get=lambda *_: execution, save=lambda value: saved.append(value)),
        actions=SimpleNamespace(get=lambda *_: action, save=lambda value, expected_version: saved.append((value, expected_version))),
        decision_cases=SimpleNamespace(get=lambda *_: case, save=lambda value, expected_version=None: saved.append((value, expected_version))),
    )
    from decision_os.application.commands.complete_action_execution import CompleteActionExecutionCommand, CompleteActionExecutionHandler
    result = CompleteActionExecutionHandler(uow, auth).handle(CompleteActionExecutionCommand(
        tenant_id=tenant_id, execution_id=execution.id, actor_id=uuid4(), outcome=ActionExecutionStatus.SUCCEEDED,
    ))
    assert result.status is ActionExecutionStatus.SUCCEEDED
    assert action.status is ActionStatus.COMPLETED
    assert case.status is CaseStatus.OUTCOME_PENDING


def test_unknown_execution_requires_explicit_reconciliation():
    tenant_id, case, decision = approved_context()
    action = Action.create(id=uuid4(), tenant_id=tenant_id, case_id=case.id, decision_id=decision.id, action_type="UPDATE_BUDGET", parameters="{}")
    action.ready()
    action.start_execution()
    execution = __import__("decision_os.domain.action", fromlist=["ActionExecution"]).ActionExecution.request(id=uuid4(), action_id=action.id, attempt=1)
    execution.start()
    execution.mark_unknown()
    auth = FakeAuthorization()
    saved = []
    uow = SimpleNamespace(
        action_executions=SimpleNamespace(get=lambda *_: execution, save=lambda value: saved.append(value)),
        actions=SimpleNamespace(get=lambda *_: action, save=lambda value, expected_version: saved.append((value, expected_version))),
        decision_cases=SimpleNamespace(get=lambda *_: case, save=lambda value, expected_version=None: saved.append((value, expected_version))),
    )
    from decision_os.application.commands.reconcile_unknown_execution import ReconcileUnknownExecutionCommand, ReconcileUnknownExecutionHandler
    result = ReconcileUnknownExecutionHandler(uow, auth).handle(ReconcileUnknownExecutionCommand(
        tenant_id=tenant_id, execution_id=execution.id, actor_id=uuid4(), observed_outcome=ActionExecutionStatus.FAILED,
    ))
    assert result.status is ActionExecutionStatus.FAILED
    assert action.status is ActionStatus.FAILED
    assert case.status is CaseStatus.OUTCOME_PENDING
