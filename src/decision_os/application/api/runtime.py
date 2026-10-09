"""Explicit production runtime composition for the first vertical slice."""
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from decision_os.application.api.app import create_app
from decision_os.application.api.dependencies import PrincipalProvider
from decision_os.application.ports.authority import AuthorizationPort, PolicyEvaluatorPort
from decision_os.infrastructure.authentication.oidc_jwt import OIDCJWTPrincipalProvider
from decision_os.infrastructure.persistence.authorization import SQLAlchemyAuthorizationAdapter
from decision_os.infrastructure.persistence.readers.decision_work_queue import SessionFactoryDecisionWorkQueueReader
from decision_os.infrastructure.persistence.resolvers.external_identity import SQLAlchemyExternalIdentityResolver
from decision_os.infrastructure.persistence.runtime_composition import (
    SessionScopedCreateDecisionCaseBoundary,
    SessionScopedTriageCaseBoundary,
    SessionScopedStartAnalysisBoundary,
    SessionScopedCreateEvidenceBoundary,
    SessionScopedAddAnalysisFindingBoundary,
    SessionScopedSubmitOptionsBoundary,
    SessionScopedAwaitDecisionBoundary,
    SessionScopedMakeDecisionBoundary,
)


def build_runtime_app(
    *,
    database_url: str | None,
    authorization: AuthorizationPort | None = None,
    principal_provider: PrincipalProvider | None = None,
    policy_evaluator: PolicyEvaluatorPort | None = None,
) -> FastAPI:
    """Build runtime composition with fail-closed database-backed RBAC by default.

    An explicitly injected AuthorizationPort may replace RBAC (for example, an
    enterprise policy adapter). Otherwise, SQLAlchemyAuthorizationAdapter checks
    active actors, tenant memberships, role assignments, and permission grants.
    If no principal provider is injected, configured OIDC/JWT validation and the
    database-backed external identity resolver are wired automatically.
    Database migrations and trusted membership provisioning must happen separately.
    """
    if not database_url or not database_url.strip():
        raise RuntimeError("SQLALCHEMY_DATABASE_URL is required to start the Decision OS runtime")

    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    try:
        if authorization is None:
            authorization = SQLAlchemyAuthorizationAdapter(session_factory)
        if principal_provider is None:
            resolver = SQLAlchemyExternalIdentityResolver(session_factory)
            principal_provider = OIDCJWTPrincipalProvider.from_environment(resolver=resolver)
    except Exception:
        engine.dispose()
        raise

    create_case_boundary = SessionScopedCreateDecisionCaseBoundary(
        session_factory=session_factory,
        authorization=authorization,
    )
    triage_case_boundary = SessionScopedTriageCaseBoundary(
        session_factory=session_factory,
        authorization=authorization,
    )
    start_analysis_boundary = SessionScopedStartAnalysisBoundary(
        session_factory=session_factory,
        authorization=authorization,
    )
    create_evidence_boundary = SessionScopedCreateEvidenceBoundary(
        session_factory=session_factory,
        authorization=authorization,
    )
    add_analysis_finding_boundary = SessionScopedAddAnalysisFindingBoundary(
        session_factory=session_factory,
        authorization=authorization,
    )
    submit_options_boundary = SessionScopedSubmitOptionsBoundary(
        session_factory=session_factory,
        authorization=authorization,
    )
    await_decision_boundary = SessionScopedAwaitDecisionBoundary(
        session_factory=session_factory,
        authorization=authorization,
    )
    make_decision_boundary = (
        SessionScopedMakeDecisionBoundary(session_factory=session_factory, authorization=authorization, policy_evaluator=policy_evaluator)
        if policy_evaluator is not None else None
    )
    queue_reader = SessionFactoryDecisionWorkQueueReader(session_factory)
    app = create_app(
        create_case_boundary=create_case_boundary,
        triage_case_boundary=triage_case_boundary,
        start_analysis_boundary=start_analysis_boundary,
        create_evidence_boundary=create_evidence_boundary,
        add_analysis_finding_boundary=add_analysis_finding_boundary,
        submit_options_boundary=submit_options_boundary,
        await_decision_boundary=await_decision_boundary,
        make_decision_boundary=make_decision_boundary,
        decision_work_queue_reader=queue_reader,
        authorization=authorization,
        principal_provider=principal_provider,
    )

    @app.on_event("shutdown")
    def dispose_database_engine() -> None:
        engine.dispose()

    return app
