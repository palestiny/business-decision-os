import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from decision_os.application.ports.authority import AuthorizationDenied, Permission
from decision_os.infrastructure.persistence.authorization import SQLAlchemyAuthorizationAdapter
from decision_os.infrastructure.persistence.models.authorization import (
    ActorModel, MembershipRoleAssignmentModel, RoleModel, TenantMembershipModel,
)
from decision_os.infrastructure.persistence.models.tenant import TenantModel

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests",
)


def test_postgres_rbac_requires_active_membership_and_explicit_permission():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    actor_id, tenant_id, other_tenant_id, membership_id = uuid4(), uuid4(), uuid4(), uuid4()
    try:
        with factory() as session:
            role = session.scalar(
                select(RoleModel).where(RoleModel.key == "decision_author", RoleModel.is_active.is_(True))
            )
            assert role is not None, "RBAC migration must seed the decision_author role"
            session.add_all([
                TenantModel(id=tenant_id, name=f"rbac-a-{tenant_id}"),
                TenantModel(id=other_tenant_id, name=f"rbac-b-{other_tenant_id}"),
                ActorModel(id=actor_id, is_active=True),
            ])
            session.flush()
            session.add(TenantMembershipModel(
                id=membership_id, actor_id=actor_id, tenant_id=tenant_id, is_active=True,
            ))
            session.flush()
            session.add(MembershipRoleAssignmentModel(
                membership_id=membership_id, role_id=role.id, is_active=True,
            ))
            session.commit()

        adapter = SQLAlchemyAuthorizationAdapter(factory)
        adapter.require(
            actor_id=actor_id, tenant_id=tenant_id,
            permission=Permission.CREATE_CASE, resource_id=uuid4(),
        )
        adapter.require(
            actor_id=actor_id, tenant_id=tenant_id,
            permission=Permission.VIEW_DECISION_WORK_QUEUE, resource_id=tenant_id,
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

        with factory() as session:
            membership = session.get(TenantMembershipModel, membership_id)
            assert membership is not None
            membership.is_active = False
            session.commit()

        with pytest.raises(AuthorizationDenied):
            adapter.require(
                actor_id=actor_id, tenant_id=tenant_id,
                permission=Permission.CREATE_CASE, resource_id=uuid4(),
            )
    finally:
        engine.dispose()



def test_postgres_read_only_reviewer_can_read_but_cannot_create_commands():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    actor_id, tenant_id, membership_id = uuid4(), uuid4(), uuid4()
    try:
        with factory() as session:
            role = session.scalar(
                select(RoleModel).where(RoleModel.key == "read_only_reviewer", RoleModel.is_active.is_(True))
            )
            assert role is not None
            session.add_all([
                TenantModel(id=tenant_id, name=f"rbac-reviewer-{tenant_id}"),
                ActorModel(id=actor_id, is_active=True),
            ])
            session.flush()
            session.add(TenantMembershipModel(
                id=membership_id, actor_id=actor_id, tenant_id=tenant_id, is_active=True,
            ))
            session.flush()
            session.add(MembershipRoleAssignmentModel(
                membership_id=membership_id, role_id=role.id, is_active=True,
            ))
            session.commit()

        adapter = SQLAlchemyAuthorizationAdapter(factory)
        adapter.require(
            actor_id=actor_id, tenant_id=tenant_id,
            permission=Permission.VIEW_DECISION_WORK_QUEUE, resource_id=tenant_id,
        )
        with pytest.raises(AuthorizationDenied):
            adapter.require(
                actor_id=actor_id, tenant_id=tenant_id,
                permission=Permission.CREATE_CASE, resource_id=uuid4(),
            )
    finally:
        engine.dispose()
