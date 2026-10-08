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
        "session", "enter", "uow", "Idempotency", "Audit", "Outbox", "handler", "boundary", "execute", "exit"
    ]
    assert all(entry[1] is session for entry in calls if entry[0] in {"uow", "Idempotency", "Audit", "Outbox"})
    assert calls[6] == ("handler", calls[2][1], authorization)
    assert calls[8][2] == "request-1"
    assert calls[-1] == ("exit", None)
