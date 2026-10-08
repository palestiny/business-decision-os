import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from uuid import uuid4

from decision_os.infrastructure.persistence.base import Base
from decision_os.infrastructure.persistence import models  # noqa: F401
from decision_os.infrastructure.persistence.models.external_identity import ExternalIdentityMappingModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel


def test_external_identity_mapping_key_is_unique_and_tenant_is_required():
    model = ExternalIdentityMappingModel.__table__
    unique = {constraint.name for constraint in model.constraints}
    assert "uq_external_identity_mapping_key" in unique
    assert model.c.tenant_id.nullable is False
    assert model.c.actor_id.nullable is False
    assert model.c.is_active.nullable is False


def test_duplicate_external_identity_mapping_is_rejected():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    tenant_id = uuid4()
    try:
        with factory() as session:
            session.add(TenantModel(id=tenant_id, name="Tenant"))
            session.flush()
            values = dict(
                issuer="https://issuer.example", subject="subject-1", tenant_key="org-1",
                actor_id=uuid4(), tenant_id=tenant_id, is_active=True,
            )
            session.add(ExternalIdentityMappingModel(**values))
            session.commit()
        with factory() as session:
            session.add(ExternalIdentityMappingModel(**values))
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()
