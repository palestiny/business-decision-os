from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from decision_os.infrastructure.persistence.base import Base
from decision_os.infrastructure.persistence import models  # noqa: F401
from decision_os.infrastructure.persistence.models.external_identity import ExternalIdentityMappingModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.resolvers.external_identity import SQLAlchemyExternalIdentityResolver
from decision_os.infrastructure.authentication.oidc_jwt import ExternalIdentity


def test_resolver_returns_only_active_exact_external_identity_mapping():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    tenant_id, actor_id = uuid4(), uuid4()
    identity = ExternalIdentity("https://issuer.example", "subject-1", "org-1")
    try:
        with factory() as session:
            session.add(TenantModel(id=tenant_id, name="Tenant"))
            session.add(ExternalIdentityMappingModel(
                issuer=identity.issuer, subject=identity.subject, tenant_key=identity.tenant_key,
                actor_id=actor_id, tenant_id=tenant_id, is_active=True,
            ))
            session.add(ExternalIdentityMappingModel(
                issuer=identity.issuer, subject="disabled-subject", tenant_key=identity.tenant_key,
                actor_id=uuid4(), tenant_id=tenant_id, is_active=False,
            ))
            session.commit()

        resolver = SQLAlchemyExternalIdentityResolver(factory)
        resolved = resolver.resolve(identity)
        assert resolved is not None
        assert resolved.actor_id == actor_id
        assert resolved.tenant_id == tenant_id
        assert resolver.resolve(ExternalIdentity(identity.issuer, "unknown", identity.tenant_key)) is None
        assert resolver.resolve(ExternalIdentity(identity.issuer, "disabled-subject", identity.tenant_key)) is None
        assert resolver.resolve(ExternalIdentity(identity.issuer, identity.subject, "other-tenant-key")) is None
        assert resolver.resolve(ExternalIdentity("https://other-issuer.example", identity.subject, identity.tenant_key)) is None
    finally:
        engine.dispose()
