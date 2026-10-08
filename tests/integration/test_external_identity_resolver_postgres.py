import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from decision_os.infrastructure.authentication.oidc_jwt import ExternalIdentity
from decision_os.infrastructure.persistence.models.external_identity import ExternalIdentityMappingModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.resolvers.external_identity import SQLAlchemyExternalIdentityResolver

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests",
)


def test_postgres_resolver_requires_exact_active_server_managed_mapping():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    tenant_id, actor_id = uuid4(), uuid4()
    issuer = f"https://issuer-{uuid4()}.example.test"
    subject = f"subject-{uuid4()}"
    tenant_key = f"org-{uuid4()}"
    try:
        with factory() as session:
            session.add(TenantModel(id=tenant_id, name=f"identity-resolver-{tenant_id}"))
            session.flush()
            session.add_all([
                ExternalIdentityMappingModel(
                    issuer=issuer, subject=subject, tenant_key=tenant_key,
                    actor_id=actor_id, tenant_id=tenant_id, is_active=True,
                ),
                ExternalIdentityMappingModel(
                    issuer=issuer, subject=f"disabled-{subject}", tenant_key=tenant_key,
                    actor_id=uuid4(), tenant_id=tenant_id, is_active=False,
                ),
            ])
            session.commit()

        resolver = SQLAlchemyExternalIdentityResolver(factory)
        mapped = resolver.resolve(ExternalIdentity(issuer, subject, tenant_key))
        assert mapped is not None
        assert mapped.actor_id == actor_id
        assert mapped.tenant_id == tenant_id
        assert resolver.resolve(ExternalIdentity(issuer, subject, f"other-{tenant_key}")) is None
        assert resolver.resolve(ExternalIdentity(issuer, f"unknown-{subject}", tenant_key)) is None
        assert resolver.resolve(ExternalIdentity(issuer, f"disabled-{subject}", tenant_key)) is None
    finally:
        engine.dispose()
