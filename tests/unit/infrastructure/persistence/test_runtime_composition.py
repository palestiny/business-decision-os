from uuid import uuid4

from decision_os.application.commands.create_decision_case import CreateDecisionCaseCommand
from decision_os.infrastructure.persistence import runtime_composition


def test_create_case_boundary_uses_one_session_for_uow_and_reliability_adapters(monkeypatch):
    session = object()
    calls = []

    class SessionContext:
        def __enter__(self):
            calls.append(("enter",))
            return session

        def __exit__(self, exc_type, exc, traceback):
            calls.append(("exit", exc_type))
            return False

    class SessionFactory:
        def __call__(self):
            calls.append(("session",))
            return SessionContext()

    class Uow:
        def __init__(self, supplied):
            calls.append(("uow", supplied))

    class Adapter:
        def __init__(self, supplied):
            calls.append((self.__class__.__name__, supplied))

    class Handler:
        def __init__(self, uow, authorization):
            calls.append(("handler", uow, authorization))

    class Boundary:
        def __init__(self, **kwargs):
            calls.append(("boundary", kwargs))

        def execute(self, command, *, idempotency_key, correlation_id=None):
            calls.append(("execute", command, idempotency_key, correlation_id))
            return "created"

    monkeypatch.setattr(runtime_composition, "SQLAlchemyUnitOfWork", Uow)
    monkeypatch.setattr(runtime_composition, "SQLAlchemyIdempotencyRepository", type("Idempotency", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyAuditRepository", type("Audit", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyOutboxRepository", type("Outbox", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "CreateDecisionCaseHandler", Handler)
    monkeypatch.setattr(runtime_composition, "CreateDecisionCaseReliabilityBoundary", Boundary)

    authorization = object()
    provider = runtime_composition.SessionScopedCreateDecisionCaseBoundary(
        session_factory=SessionFactory(),
        authorization=authorization,
    )
    command = CreateDecisionCaseCommand(
        tenant_id=uuid4(), actor_id=uuid4(), case_type="PROJECT_MARGIN_RISK", title="Margin risk"
    )

    result = provider.execute(command, idempotency_key="request-1")

    assert result == "created"
    assert [entry[0] for entry in calls] == [
        "session", "enter", "uow", "handler", "Idempotency", "Audit", "Outbox", "boundary", "execute", "exit"
    ]
    assert all(entry[1] is session for entry in calls if entry[0] in {"uow", "Idempotency", "Audit", "Outbox"})
    assert calls[3][0] == "handler"
    assert isinstance(calls[3][1], Uow)
    assert calls[3][2] is authorization
    assert calls[8][2] == "request-1"
    assert calls[-1] == ("exit", None)

def test_runtime_refuses_to_start_without_database_url():
    from decision_os.application.api.runtime import build_runtime_app

    try:
        build_runtime_app(
            database_url=None,
            authorization=object(),
            principal_provider=lambda request: None,
        )
    except RuntimeError as exc:
        assert str(exc) == "SQLALCHEMY_DATABASE_URL is required to start the Decision OS runtime"
    else:
        raise AssertionError("runtime should fail fast without a database URL")



def test_concurrent_create_case_executions_use_distinct_sessions(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock

    from decision_os.infrastructure.persistence import runtime_composition

    barrier = Barrier(2)
    lock = Lock()
    opened_sessions = []
    active_sessions = set()
    closed_sessions = []

    class Session:
        pass

    class SessionContext:
        def __init__(self):
            self.session = Session()

        def __enter__(self):
            with lock:
                opened_sessions.append(self.session)
                active_sessions.add(self.session)
            return self.session

        def __exit__(self, exc_type, exc, traceback):
            with lock:
                active_sessions.remove(self.session)
                closed_sessions.append(self.session)
            return False

    class SessionFactory:
        def __call__(self):
            return SessionContext()

    class Uow:
        def __init__(self, session):
            self.session = session

    class Adapter:
        def __init__(self, session):
            self.session = session

    class Handler:
        def __init__(self, uow, authorization):
            self.uow = uow

    class Boundary:
        def __init__(self, **kwargs):
            self.uow = kwargs["uow"]

        def execute(self, command, *, idempotency_key, correlation_id=None):
            barrier.wait(timeout=5)
            with lock:
                assert self.uow.session in active_sessions
                return self.uow.session

    monkeypatch.setattr(runtime_composition, "SQLAlchemyUnitOfWork", Uow)
    monkeypatch.setattr(runtime_composition, "SQLAlchemyIdempotencyRepository", Adapter)
    monkeypatch.setattr(runtime_composition, "SQLAlchemyAuditRepository", Adapter)
    monkeypatch.setattr(runtime_composition, "SQLAlchemyOutboxRepository", Adapter)
    monkeypatch.setattr(runtime_composition, "CreateDecisionCaseHandler", Handler)
    monkeypatch.setattr(runtime_composition, "CreateDecisionCaseReliabilityBoundary", Boundary)

    provider = runtime_composition.SessionScopedCreateDecisionCaseBoundary(
        session_factory=SessionFactory(),
        authorization=object(),
    )
    command = CreateDecisionCaseCommand(
        tenant_id=uuid4(), actor_id=uuid4(), case_type="PROJECT_MARGIN_RISK", title="Concurrent risk"
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(provider.execute, command, idempotency_key="concurrent-1")
        second = executor.submit(provider.execute, command, idempotency_key="concurrent-2")
        first_session, second_session = first.result(timeout=10), second.result(timeout=10)

    assert first_session is not second_session
    assert len(opened_sessions) == 2
    assert set(opened_sessions) == set(closed_sessions)
    assert not active_sessions



def test_triage_case_boundary_uses_one_session_for_all_adapters(monkeypatch):
    from decision_os.application.commands.triage_case import TriageCaseCommand
    from decision_os.infrastructure.persistence import runtime_composition

    session = object()
    calls = []

    class SessionContext:
        def __enter__(self):
            calls.append(("enter",))
            return session

        def __exit__(self, exc_type, exc, traceback):
            calls.append(("exit", exc_type))
            return False

    class SessionFactory:
        def __call__(self):
            calls.append(("session",))
            return SessionContext()

    class Uow:
        def __init__(self, supplied):
            calls.append(("uow", supplied))

    class Adapter:
        def __init__(self, supplied):
            calls.append((self.__class__.__name__, supplied))

    class Handler:
        def __init__(self, uow, authorization):
            calls.append(("handler", uow, authorization))

    class Boundary:
        def __init__(self, **kwargs):
            calls.append(("boundary", kwargs))

        def execute(self, command, *, idempotency_key, correlation_id=None):
            calls.append(("execute", command, idempotency_key, correlation_id))
            return "triaged"

    monkeypatch.setattr(runtime_composition, "SQLAlchemyUnitOfWork", Uow)
    monkeypatch.setattr(runtime_composition, "SQLAlchemyIdempotencyRepository", type("Idempotency", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyAuditRepository", type("Audit", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyOutboxRepository", type("Outbox", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "TriageCaseHandler", Handler)
    monkeypatch.setattr(runtime_composition, "TriageCaseReliabilityBoundary", Boundary)

    authorization = object()
    provider = runtime_composition.SessionScopedTriageCaseBoundary(
        session_factory=SessionFactory(),
        authorization=authorization,
    )
    command = TriageCaseCommand(
        tenant_id=uuid4(), case_id=uuid4(), actor_id=uuid4(), correlation_id=uuid4()
    )
    result = provider.execute(command, idempotency_key="triage-session-1", correlation_id=command.correlation_id)

    assert result == "triaged"
    assert [entry[0] for entry in calls] == [
        "session", "enter", "uow", "handler", "Idempotency", "Audit", "Outbox", "boundary", "execute", "exit"
    ]
    assert all(entry[1] is session for entry in calls if entry[0] in {"uow", "Idempotency", "Audit", "Outbox"})
    assert calls[-1] == ("exit", None)


def test_await_decision_boundary_uses_one_session_for_all_adapters(monkeypatch):
    from decision_os.application.commands.await_decision import AwaitDecisionCommand
    from decision_os.infrastructure.persistence import runtime_composition

    session = object()
    calls = []

    class SessionContext:
        def __enter__(self):
            calls.append(("enter",))
            return session
        def __exit__(self, exc_type, exc, traceback):
            calls.append(("exit", exc_type))
            return False
    class SessionFactory:
        def __call__(self):
            calls.append(("session",))
            return SessionContext()
    class Uow:
        def __init__(self, supplied):
            calls.append(("uow", supplied))
    class Adapter:
        def __init__(self, supplied):
            calls.append((self.__class__.__name__, supplied))
    class Handler:
        def __init__(self, uow, authorization):
            calls.append(("handler", uow, authorization))
    class Boundary:
        def __init__(self, **kwargs):
            calls.append(("boundary", kwargs))
        def execute(self, command, *, idempotency_key, correlation_id=None):
            calls.append(("execute", command, idempotency_key, correlation_id))
            return "awaiting-decision"

    monkeypatch.setattr(runtime_composition, "SQLAlchemyUnitOfWork", Uow)
    monkeypatch.setattr(runtime_composition, "SQLAlchemyIdempotencyRepository", type("Idempotency", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyAuditRepository", type("Audit", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyOutboxRepository", type("Outbox", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "AwaitDecisionHandler", Handler)
    monkeypatch.setattr(runtime_composition, "AwaitDecisionReliabilityBoundary", Boundary)

    authorization = object()
    provider = runtime_composition.SessionScopedAwaitDecisionBoundary(session_factory=SessionFactory(), authorization=authorization)
    command = AwaitDecisionCommand(tenant_id=uuid4(), case_id=uuid4(), actor_id=uuid4(), correlation_id=uuid4())
    result = provider.execute(command, idempotency_key="await-decision-1", correlation_id=command.correlation_id)

    assert result == "awaiting-decision"
    assert [entry[0] for entry in calls] == [
        "session", "enter", "uow", "handler", "Idempotency", "Audit", "Outbox", "boundary", "execute", "exit"
    ]
    assert all(entry[1] is session for entry in calls if entry[0] in {"uow", "Idempotency", "Audit", "Outbox"})
    assert calls[-1] == ("exit", None)


def test_make_decision_boundary_uses_one_session_and_injected_policy(monkeypatch):
    from decision_os.application.commands.make_decision import MakeDecisionCommand
    from decision_os.infrastructure.persistence import runtime_composition

    session, calls = object(), []

    class Uow:
        def __init__(self, supplied):
            self.decision_options = object()
            calls.append(("uow", supplied))
    class Adapter:
        def __init__(self, supplied):
            calls.append((self.__class__.__name__, supplied))
    class Handler:
        def __init__(self, uow, authorization, policy_evaluator):
            calls.append(("handler", uow, authorization, policy_evaluator))
    class Boundary:
        def __init__(self, **kwargs):
            calls.append(("boundary", kwargs))
        def execute(self, command, *, idempotency_key, correlation_id=None):
            calls.append(("execute", command, idempotency_key, correlation_id))
            return "decision"
    class SessionContext:
        def __enter__(self): return session
        def __exit__(self, exc_type, exc, traceback): calls.append(("exit", exc_type)); return False
    class SessionFactory:
        def __call__(self): return SessionContext()

    monkeypatch.setattr(runtime_composition, "SQLAlchemyUnitOfWork", Uow)
    monkeypatch.setattr(runtime_composition, "SQLAlchemyIdempotencyRepository", type("Idempotency", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyAuditRepository", type("Audit", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyOutboxRepository", type("Outbox", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "MakeDecisionHandler", Handler)
    monkeypatch.setattr(runtime_composition, "MakeDecisionReliabilityBoundary", Boundary)

    authorization, policy = object(), object()
    provider = runtime_composition.SessionScopedMakeDecisionBoundary(
        session_factory=SessionFactory(), authorization=authorization, policy_evaluator=policy
    )
    command = MakeDecisionCommand(tenant_id=uuid4(), case_id=uuid4(), decision_id=uuid4(),
                                  option_ids=(uuid4(),), rationale="Protect margin", actor_id=uuid4())
    assert provider.execute(command, idempotency_key="make-decision-1") == "decision"
    handler_call = next(call for call in calls if call[0] == "handler")
    assert handler_call[2] is authorization and handler_call[3] is policy
    boundary_kwargs = next(call[1] for call in calls if call[0] == "boundary")
    assert boundary_kwargs["option_repository"] is not None
    assert calls[-1] == ("exit", None)


def test_approve_decision_boundary_uses_one_session_for_all_adapters(monkeypatch):
    from decision_os.application.commands.approve_decision import ApproveDecisionCommand
    from decision_os.infrastructure.persistence import runtime_composition

    session, calls = object(), []
    class Uow:
        def __init__(self, supplied): calls.append(("uow", supplied))
    class Adapter:
        def __init__(self, supplied): calls.append((self.__class__.__name__, supplied))
    class Handler:
        def __init__(self, uow, authorization): calls.append(("handler", uow, authorization))
    class Boundary:
        def __init__(self, **kwargs): calls.append(("boundary", kwargs))
        def execute(self, command, *, idempotency_key, correlation_id=None):
            calls.append(("execute", command, idempotency_key, correlation_id)); return "approved"
    class SessionContext:
        def __enter__(self): return session
        def __exit__(self, exc_type, exc, traceback): calls.append(("exit", exc_type)); return False
    class SessionFactory:
        def __call__(self): return SessionContext()

    monkeypatch.setattr(runtime_composition, "SQLAlchemyUnitOfWork", Uow)
    monkeypatch.setattr(runtime_composition, "SQLAlchemyIdempotencyRepository", type("Idempotency", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyAuditRepository", type("Audit", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyOutboxRepository", type("Outbox", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "ApproveDecisionHandler", Handler)
    monkeypatch.setattr(runtime_composition, "ApproveDecisionReliabilityBoundary", Boundary)

    authorization = object()
    provider = runtime_composition.SessionScopedApproveDecisionBoundary(session_factory=SessionFactory(), authorization=authorization)
    command = ApproveDecisionCommand(tenant_id=uuid4(), case_id=uuid4(), decision_id=uuid4(), actor_id=uuid4())
    assert provider.execute(command, idempotency_key="approve-decision-1") == "approved"
    handler_call = next(call for call in calls if call[0] == "handler")
    assert handler_call[2] is authorization
    assert calls[-1] == ("exit", None)


def test_reject_decision_boundary_uses_one_session_for_all_adapters(monkeypatch):
    from decision_os.application.commands.reject_decision import RejectDecisionCommand
    from decision_os.infrastructure.persistence import runtime_composition

    session, calls = object(), []
    class Uow:
        def __init__(self, supplied): calls.append(("uow", supplied))
    class Adapter:
        def __init__(self, supplied): calls.append((self.__class__.__name__, supplied))
    class Handler:
        def __init__(self, uow, authorization): calls.append(("handler", uow, authorization))
    class Boundary:
        def __init__(self, **kwargs): calls.append(("boundary", kwargs))
        def execute(self, command, *, idempotency_key, correlation_id=None):
            calls.append(("execute", command, idempotency_key, correlation_id)); return "rejected"
    class SessionContext:
        def __enter__(self): return session
        def __exit__(self, exc_type, exc, traceback): calls.append(("exit", exc_type)); return False
    class SessionFactory:
        def __call__(self): return SessionContext()

    monkeypatch.setattr(runtime_composition, "SQLAlchemyUnitOfWork", Uow)
    monkeypatch.setattr(runtime_composition, "SQLAlchemyIdempotencyRepository", type("Idempotency", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyAuditRepository", type("Audit", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyOutboxRepository", type("Outbox", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "RejectDecisionHandler", Handler)
    monkeypatch.setattr(runtime_composition, "RejectDecisionReliabilityBoundary", Boundary)

    authorization = object()
    provider = runtime_composition.SessionScopedRejectDecisionBoundary(session_factory=SessionFactory(), authorization=authorization)
    command = RejectDecisionCommand(tenant_id=uuid4(), case_id=uuid4(), decision_id=uuid4(), actor_id=uuid4())
    assert provider.execute(command, idempotency_key="reject-decision-1") == "rejected"
    handler_call = next(call for call in calls if call[0] == "handler")
    assert handler_call[2] is authorization
    assert calls[-1] == ("exit", None)


def test_create_action_boundary_uses_one_session_for_all_adapters(monkeypatch):
    from decision_os.application.commands.create_action import CreateActionCommand
    from decision_os.infrastructure.persistence import runtime_composition

    session, calls = object(), []
    class Uow:
        def __init__(self, supplied): calls.append(("uow", supplied))
    class Adapter:
        def __init__(self, supplied): calls.append((self.__class__.__name__, supplied))
    class Handler:
        def __init__(self, uow, authorization): calls.append(("handler", uow, authorization))
    class Boundary:
        def __init__(self, **kwargs): calls.append(("boundary", kwargs))
        def execute(self, command, *, idempotency_key, correlation_id=None):
            calls.append(("execute", command, idempotency_key, correlation_id)); return "ready-action"
    class SessionContext:
        def __enter__(self): return session
        def __exit__(self, exc_type, exc, traceback): calls.append(("exit", exc_type)); return False
    class SessionFactory:
        def __call__(self): return SessionContext()

    monkeypatch.setattr(runtime_composition, "SQLAlchemyUnitOfWork", Uow)
    monkeypatch.setattr(runtime_composition, "SQLAlchemyIdempotencyRepository", type("Idempotency", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyAuditRepository", type("Audit", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyOutboxRepository", type("Outbox", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "CreateActionHandler", Handler)
    monkeypatch.setattr(runtime_composition, "CreateActionReliabilityBoundary", Boundary)

    authorization = object()
    provider = runtime_composition.SessionScopedCreateActionBoundary(session_factory=SessionFactory(), authorization=authorization)
    command = CreateActionCommand(tenant_id=uuid4(), case_id=uuid4(), decision_id=uuid4(),
                                  actor_id=uuid4(), action_type="COST_REDUCTION", parameters="5 percent")
    assert provider.execute(command, idempotency_key="create-action-1") == "ready-action"
    handler_call = next(call for call in calls if call[0] == "handler")
    assert handler_call[2] is authorization
    assert calls[-1] == ("exit", None)


def test_start_action_boundary_uses_one_session_for_all_adapters(monkeypatch):
    from decision_os.application.commands.start_action import StartActionCommand
    from decision_os.infrastructure.persistence import runtime_composition

    session, calls = object(), []
    class Uow:
        def __init__(self, supplied): calls.append(("uow", supplied))
    class Adapter:
        def __init__(self, supplied): calls.append((self.__class__.__name__, supplied))
    class Handler:
        def __init__(self, uow, authorization): calls.append(("handler", uow, authorization))
    class Boundary:
        def __init__(self, **kwargs): calls.append(("boundary", kwargs))
        def execute(self, command, *, idempotency_key, correlation_id=None):
            calls.append(("execute", command, idempotency_key, correlation_id)); return "running-execution"
    class SessionContext:
        def __enter__(self): return session
        def __exit__(self, exc_type, exc, traceback): calls.append(("exit", exc_type)); return False
    class SessionFactory:
        def __call__(self): return SessionContext()

    monkeypatch.setattr(runtime_composition, "SQLAlchemyUnitOfWork", Uow)
    monkeypatch.setattr(runtime_composition, "SQLAlchemyIdempotencyRepository", type("Idempotency", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyAuditRepository", type("Audit", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "SQLAlchemyOutboxRepository", type("Outbox", (Adapter,), {}))
    monkeypatch.setattr(runtime_composition, "StartActionHandler", Handler)
    monkeypatch.setattr(runtime_composition, "StartActionReliabilityBoundary", Boundary)

    authorization = object()
    provider = runtime_composition.SessionScopedStartActionBoundary(session_factory=SessionFactory(), authorization=authorization)
    command = StartActionCommand(tenant_id=uuid4(), action_id=uuid4(), actor_id=uuid4())
    assert provider.execute(command, idempotency_key="start-action-1") == "running-execution"
    handler_call = next(call for call in calls if call[0] == "handler")
    assert handler_call[2] is authorization
    assert calls[-1] == ("exit", None)
