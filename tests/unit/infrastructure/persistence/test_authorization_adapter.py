from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from decision_os.application.ports.authority import AuthorizationDenied, Permission, PolicyEvaluationUnavailable
from decision_os.infrastructure.persistence import models  # noqa: F401
from decision_os.infrastructure.persistence.authorization import SQLAlchemyAuthorizationAdapter
from decision_os.infrastructure.persistence.base import Base
from decision_os.infrastructure.persistence.models.authorization import (
    ActorModel, MembershipRoleAssignmentModel, RoleModel, RolePermissionModel, TenantMembershipModel,
)
from decision_os.infrastructure.persistence.models.tenant import TenantModel


def test_rbac_grants_only_active_tenant_members_with_assigned_permission():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    actor_id, tenant_id, other_tenant_id = uuid4(), uuid4(), uuid4()
    role_id, membership_id = uuid4(), uuid4()
    try:
        with factory() as session:
            session.add_all([
                TenantModel(id=tenant_id, name="Tenant A"),
                TenantModel(id=other_tenant_id, name="Tenant B"),
                ActorModel(id=actor_id, is_active=True),
                RoleModel(id=role_id, key="decision_author", name="Decision Author", is_active=True),
            ])
            session.flush()
            session.add_all([
                TenantMembershipModel(id=membership_id, actor_id=actor_id, tenant_id=tenant_id, is_active=True),
                RolePermissionModel(role_id=role_id, permission=Permission.CREATE_CASE.value),
            ])
            session.flush()
            session.add(MembershipRoleAssignmentModel(
                membership_id=membership_id, role_id=role_id, is_active=True,
            ))
            session.commit()

        adapter = SQLAlchemyAuthorizationAdapter(factory)
        adapter.require(
            actor_id=actor_id, tenant_id=tenant_id, permission=Permission.CREATE_CASE, resource_id=uuid4()
        )
        with pytest.raises(AuthorizationDenied):
            adapter.require(
                actor_id=actor_id, tenant_id=other_tenant_id,
                permission=Permission.CREATE_CASE, resource_id=uuid4(),
            )
        with pytest.raises(AuthorizationDenied):
            adapter.require(
                actor_id=actor_id, tenant_id=tenant_id,
                permission=Permission.APPROVE_DECISION, resource_id=uuid4(),
            )
    finally:
        engine.dispose()


@pytest.mark.parametrize("inactive", ["actor", "membership", "assignment", "role"])
def test_rbac_denies_when_any_authorization_layer_is_inactive(inactive):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    actor_id, tenant_id, role_id, membership_id = uuid4(), uuid4(), uuid4(), uuid4()
    try:
        with factory() as session:
            session.add(TenantModel(id=tenant_id, name="Tenant"))
            session.add(ActorModel(id=actor_id, is_active=inactive != "actor"))
            session.add(RoleModel(id=role_id, key="author", name="Author", is_active=inactive != "role"))
            session.flush()
            session.add(TenantMembershipModel(
                id=membership_id, actor_id=actor_id, tenant_id=tenant_id, is_active=inactive != "membership",
            ))
            session.add(RolePermissionModel(role_id=role_id, permission=Permission.CREATE_CASE.value))
            session.flush()
            session.add(MembershipRoleAssignmentModel(
                membership_id=membership_id, role_id=role_id, is_active=inactive != "assignment",
            ))
            session.commit()

        with pytest.raises(AuthorizationDenied):
            SQLAlchemyAuthorizationAdapter(factory).require(
                actor_id=actor_id, tenant_id=tenant_id,
                permission=Permission.CREATE_CASE, resource_id=uuid4(),
            )
    finally:
        engine.dispose()


def test_rbac_fails_closed_when_policy_store_is_unavailable():
    class BrokenFactory:
        def __call__(self):
            raise SQLAlchemyError("connection unavailable")

    with pytest.raises(PolicyEvaluationUnavailable):
        SQLAlchemyAuthorizationAdapter(BrokenFactory()).require(
            actor_id=uuid4(), tenant_id=uuid4(),
            permission=Permission.CREATE_CASE, resource_id=uuid4(),
        )
