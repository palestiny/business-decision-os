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
