import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from decision_os.application.api.runtime import build_runtime_app
from decision_os.infrastructure.authentication import oidc_jwt
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests",
)


def test_runtime_oidc_wiring_rejects_invalid_signature_and_unmapped_identity(monkeypatch):
    issuer = "https://runtime-oidc.example.test"
    audience = "decision-os-api"
    trusted_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    trusted_public = trusted_private.public_key()
    attacker_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class JWKClient:
        def __init__(self, url):
            assert url == f"{issuer}/jwks"

        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=trusted_public)

    monkeypatch.setattr(oidc_jwt, "PyJWKClient", JWKClient)
    monkeypatch.setenv("OIDC_ISSUER", issuer)
    monkeypatch.setenv("OIDC_AUDIENCE", audience)
    monkeypatch.setenv("OIDC_JWKS_URL", f"{issuer}/jwks")
    monkeypatch.setenv("OIDC_TENANT_CLAIM", "tenant_key")

    now = datetime.now(timezone.utc)
    claims = {
        "iss": issuer, "aud": audience, "sub": f"unknown-{uuid4()}",
        "tenant_key": f"unknown-org-{uuid4()}",
        "iat": now, "exp": now + timedelta(minutes=5),
    }
    invalid_signature = jwt.encode(claims, attacker_private, algorithm="RS256")
    trusted_but_unmapped = jwt.encode(claims, trusted_private, algorithm="RS256")

    app = build_runtime_app(database_url=DATABASE_URL, authorization=object())
    with TestClient(app) as client:
        invalid_response = client.get(
            "/api/v1/decision-work-queue",
            headers={"Authorization": f"Bearer {invalid_signature}"},
        )
        unmapped_response = client.get(
            "/api/v1/decision-work-queue",
            headers={"Authorization": f"Bearer {trusted_but_unmapped}"},
        )

    assert invalid_response.status_code == 401, invalid_response.text
    assert unmapped_response.status_code == 401, unmapped_response.text
