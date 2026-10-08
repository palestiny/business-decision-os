"""Explicit production runtime composition for the first vertical slice."""
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from decision_os.application.api.app import create_app
from decision_os.application.api.dependencies import PrincipalProvider
from decision_os.application.ports.authority import AuthorizationPort
from decision_os.infrastructure.persistence.readers.decision_work_queue import SessionFactoryDecisionWorkQueueReader
from decision_os.infrastructure.persistence.runtime_composition import SessionScopedCreateDecisionCaseBoundary


def build_runtime_app(
    *,
    database_url: str | None,
    authorization: AuthorizationPort,
    principal_provider: PrincipalProvider,
) -> FastAPI:
    """Build the runtime with explicit authentication and authorization dependencies.

    This function intentionally does not invent an authentication provider or an
    allow-all authorization policy. Database migrations must be applied separately.
    """
    if not database_url or not database_url.strip():
        raise RuntimeError("SQLALCHEMY_DATABASE_URL is required to start the Decision OS runtime")
    if authorization is None:
        raise RuntimeError("an explicit AuthorizationPort implementation is required")
    if principal_provider is None:
        raise RuntimeError("an explicit authenticated PrincipalProvider is required")

    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    create_case_boundary = SessionScopedCreateDecisionCaseBoundary(
        session_factory=session_factory,
        authorization=authorization,
    )
    queue_reader = SessionFactoryDecisionWorkQueueReader(session_factory)
    app = create_app(
        create_case_boundary=create_case_boundary,
        decision_work_queue_reader=queue_reader,
        principal_provider=principal_provider,
    )

    @app.on_event("shutdown")
    def dispose_database_engine() -> None:
        engine.dispose()

    return app
