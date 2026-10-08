from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Request
from jwt.exceptions import PyJWTError

from decision_os.application.ports.authentication import AuthenticationRequired
from decision_os.infrastructure.authentication import oidc_jwt
from decision_os.infrastructure.authentication.oidc_jwt import (
    ExternalIdentity,
    InternalIdentity,
    OIDCJWTPrincipalProvider,
)


class Resolver:
    def __init__(self, identity):
        self.identity = identity
        self.seen = []

    def resolve(self, identity: ExternalIdentity):
        self.seen.append(identity)
        return self.identity


def make_request(token: str | None) -> Request:
    headers = [] if token is None else [(b"authorization", f"Bearer {token}".encode())]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


@pytest.fixture
def key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture
def provider(monkeypatch, key_pair):
    private_key, public_key = key_pair

    class JWKClient:
        def __init__(self, url):
            assert url == "https://identity.example.test/.well-known/jwks.json"

        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=public_key)

    monkeypatch.setattr(oidc_jwt, "PyJWKClient", JWKClient)
    resolver = Resolver(InternalIdentity(actor_id=uuid4(), tenant_id=uuid4()))
    instance = OIDCJWTPrincipalProvider(
        issuer="https://identity.example.test/",
        audience="decision-os-api",
        jwks_url="https://identity.example.test/.well-known/jwks.json",
        tenant_claim="tenant_key",
        resolver=resolver,
    )
    return instance, resolver, private_key


def token(private_key, **overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "iss": "https://identity.example.test",
        "aud": "decision-os-api",
        "sub": "external-user-42",
        "tenant_key": "org-acme",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256")


def test_valid_token_maps_verified_external_identity_to_internal_principal(provider):
    instance, resolver, private_key = provider

    principal = instance(make_request(token(private_key)))

    assert principal.actor_id == resolver.identity.actor_id
    assert principal.tenant_id == resolver.identity.tenant_id
    assert resolver.seen == [
        ExternalIdentity(
            issuer="https://identity.example.test",
            subject="external-user-42",
            tenant_key="org-acme",
        )
    ]


@pytest.mark.parametrize("header", [None, "Basic abc", "Bearer "])
def test_missing_or_non_bearer_credentials_fail_closed(provider, header):
    instance, _, _ = provider
    request = Request({
        "type": "http", "method": "GET", "path": "/",
        "headers": [] if header is None else [(b"authorization", header.encode())],
    })
    with pytest.raises(AuthenticationRequired):
        instance(request)


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://attacker.example.test"},
        {"aud": "other-api"},
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
        {"tenant_key": ""},
        {"sub": ""},
    ],
)
def test_invalid_token_claims_fail_closed(provider, overrides):
    instance, resolver, private_key = provider
    with pytest.raises(AuthenticationRequired):
        instance(make_request(token(private_key, **overrides)))
    assert resolver.seen == []


def test_unmapped_external_identity_is_rejected(provider):
    instance, _, private_key = provider
    instance._resolver = Resolver(None)

    with pytest.raises(AuthenticationRequired):
        instance(make_request(token(private_key)))


def test_signature_from_untrusted_key_is_rejected(provider):
    instance, _, _ = provider
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(AuthenticationRequired):
        instance(make_request(token(attacker_key)))


def test_provider_requires_explicit_security_configuration(key_pair):
    with pytest.raises(ValueError):
        OIDCJWTPrincipalProvider(
            issuer="",
            audience="api",
            jwks_url="https://identity.example.test/jwks",
            tenant_claim="tenant_key",
            resolver=Resolver(None),
        )
