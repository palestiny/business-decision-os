"""Fail-closed OIDC JWT bearer authentication adapter.

The issuer, audience, JWKS endpoint, and claim mapping are deployment configuration.
External identity-to-internal UUID mapping is delegated to an explicit resolver.
"""
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import jwt
from fastapi import Request
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from decision_os.application.ports.authentication import AuthenticatedPrincipal, AuthenticationRequired


@dataclass(frozen=True)
class ExternalIdentity:
    issuer: str
    subject: str
    tenant_key: str


@dataclass(frozen=True)
class InternalIdentity:
    actor_id: UUID
    tenant_id: UUID


class ExternalIdentityResolver(Protocol):
    """Resolve a verified external identity to internal actor and tenant IDs."""

    def resolve(self, identity: ExternalIdentity) -> InternalIdentity | None: ...


class OIDCJWTPrincipalProvider:
    """Validate RS256 bearer tokens and map verified claims to an internal principal."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        tenant_claim: str,
        resolver: ExternalIdentityResolver,
        clock_skew_seconds: int = 30,
    ) -> None:
        if not issuer.strip() or not audience.strip() or not jwks_url.strip() or not tenant_claim.strip():
            raise ValueError("issuer, audience, jwks_url, and tenant_claim are required")
        if clock_skew_seconds < 0 or clock_skew_seconds > 120:
            raise ValueError("clock_skew_seconds must be between 0 and 120")
        if resolver is None:
            raise ValueError("an explicit external identity resolver is required")
        self._issuer = issuer.rstrip("/")
        self._audience = audience
        self._jwks_client = PyJWKClient(jwks_url)
        self._tenant_claim = tenant_claim
        self._resolver = resolver
        self._clock_skew_seconds = clock_skew_seconds

    def __call__(self, request: Request) -> AuthenticatedPrincipal:
        authorization = request.headers.get("Authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationRequired("bearer access token required")

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token.strip()).key
            claims = jwt.decode(
                token.strip(),
                signing_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
                leeway=self._clock_skew_seconds,
                options={"require": ["exp", "iat", "iss", "sub", "aud"]},
            )
        except (PyJWTError, ValueError, TypeError) as exc:
            raise AuthenticationRequired("bearer access token is invalid") from exc
        except Exception as exc:
            # JWKS transport/key lookup failures must fail closed without leaking details.
            raise AuthenticationRequired("bearer access token could not be verified") from exc

        tenant_key = claims.get(self._tenant_claim)
        subject = claims.get("sub")
        issuer = claims.get("iss")
        if not all(isinstance(value, str) and value.strip() for value in (tenant_key, subject, issuer)):
            raise AuthenticationRequired("required identity claims are missing")

        identity = self._resolver.resolve(
            ExternalIdentity(issuer=issuer, subject=subject, tenant_key=tenant_key)
        )
        if identity is None:
            raise AuthenticationRequired("external identity is not mapped")
        if not isinstance(identity.actor_id, UUID) or not isinstance(identity.tenant_id, UUID):
            raise AuthenticationRequired("external identity mapping is invalid")
        return AuthenticatedPrincipal(actor_id=identity.actor_id, tenant_id=identity.tenant_id)
