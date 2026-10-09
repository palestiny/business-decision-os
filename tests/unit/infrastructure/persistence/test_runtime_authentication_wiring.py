import pytest
from fastapi import FastAPI

from decision_os.application.api import runtime
from decision_os.infrastructure.persistence.authorization import SQLAlchemyAuthorizationAdapter


def test_runtime_requires_explicit_oidc_configuration_when_provider_is_not_injected(monkeypatch):
    for name in ("OIDC_ISSUER", "OIDC_AUDIENCE", "OIDC_JWKS_URL", "OIDC_TENANT_CLAIM"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="Missing required OIDC configuration"):
        runtime.build_runtime_app(database_url="sqlite+pysqlite:///:memory:", authorization=object())


def test_runtime_injects_configured_oidc_provider_when_no_provider_is_supplied(monkeypatch):
    expected_provider = lambda request: None
    captured = {}

    class Resolver:
        def __init__(self, session_factory):
            captured["resolver_session_factory"] = session_factory

    class ProviderFactory:
        @classmethod
        def from_environment(cls, *, resolver):
            captured["resolver"] = resolver
            return expected_provider

    def create_app(**kwargs):
        captured["app_kwargs"] = kwargs
        return FastAPI()

    monkeypatch.setattr(runtime, "SQLAlchemyExternalIdentityResolver", Resolver)
    monkeypatch.setattr(runtime, "OIDCJWTPrincipalProvider", ProviderFactory)
    monkeypatch.setattr(runtime, "create_app", create_app)

    app = runtime.build_runtime_app(
        database_url="sqlite+pysqlite:///:memory:",
        authorization=object(),
    )
    try:
        assert isinstance(app, FastAPI)
        assert captured["app_kwargs"]["principal_provider"] is expected_provider
        assert isinstance(captured["resolver"], Resolver)
        assert captured["resolver_session_factory"] is not None
    finally:
        for handler in app.router.on_shutdown:
            handler()


def test_runtime_defaults_to_database_backed_fail_closed_authorization(monkeypatch):
    captured = {}

    def create_app(**kwargs):
        captured["app_kwargs"] = kwargs
        return FastAPI()

    monkeypatch.setattr(runtime, "create_app", create_app)
    app = runtime.build_runtime_app(
        database_url="sqlite+pysqlite:///:memory:",
        principal_provider=lambda request: None,
    )
    try:
        boundary = captured["app_kwargs"]["create_case_boundary"]
        assert isinstance(boundary._authorization, SQLAlchemyAuthorizationAdapter)
    finally:
        for handler in app.router.on_shutdown:
            handler()


def test_runtime_composes_default_require_approval_policy(monkeypatch):
    from decision_os.application.approval_policy import RequireApprovalForEveryDecisionPolicy

    captured = {}

    def create_app(**kwargs):
        captured["app_kwargs"] = kwargs
        return FastAPI()

    monkeypatch.setattr(runtime, "create_app", create_app)
    app = runtime.build_runtime_app(
        database_url="sqlite+pysqlite:///:memory:",
        principal_provider=lambda request: None,
    )
    try:
        boundary = captured["app_kwargs"]["make_decision_boundary"]
        assert boundary is not None
        assert isinstance(boundary._policy_evaluator, RequireApprovalForEveryDecisionPolicy)
    finally:
        for handler in app.router.on_shutdown:
            handler()


def test_runtime_preserves_explicit_policy_evaluator_override(monkeypatch):
    captured = {}
    expected_policy = object()

    def create_app(**kwargs):
        captured["app_kwargs"] = kwargs
        return FastAPI()

    monkeypatch.setattr(runtime, "create_app", create_app)
    app = runtime.build_runtime_app(
        database_url="sqlite+pysqlite:///:memory:",
        principal_provider=lambda request: None,
        policy_evaluator=expected_policy,
    )
    try:
        assert captured["app_kwargs"]["make_decision_boundary"]._policy_evaluator is expected_policy
    finally:
        for handler in app.router.on_shutdown:
            handler()
