import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from decision_os.application.ports.authority import AuthorizationDenied, Permission
from decision_os.infrastructure.persistence.authorization import SQLAlchemyAuthorizationAdapter
from decision_os.infrastructure.persistence.models.authorization import ActorModel, MembershipRoleAssignmentModel, RoleModel, TenantMembershipModel
from decision_os.infrastructure.persistence.models.authorization_admin_audit import AuthorizationAdminAuditModel
from decision_os.infrastructure.persistence.models.external_identity import ExternalIdentityMappingModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.provisioning import ProvisioningError, SQLAlchemyAuthorizationProvisioner

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="SQLALCHEMY_DATABASE_URL is required")


def test_postgres_provisioning_is_atomic_idempotent_audited_and_revocable():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    tenant_id = uuid4()
    issuer, subject, tenant_key = "https://issuer.example", f"sub-{uuid4()}", f"tenant-{uuid4()}"
    try:
        with factory() as session:
            session.add(TenantModel(id=tenant_id, name=f"provision-{tenant_id}"))
            session.commit()
        service = SQLAlchemyAuthorizationProvisioner(factory)
        plan = service.plan_provision(issuer=issuer, subject=subject, tenant_key=tenant_key, tenant_id=tenant_id, role_key="read_only_reviewer")
        result = service.apply_provision(plan=plan, operator="deployment-operator")
        repeat_plan = service.plan_provision(issuer=issuer, subject=subject, tenant_key=tenant_key, tenant_id=tenant_id, role_key="read_only_reviewer")
        repeat = service.apply_provision(plan=repeat_plan, operator="deployment-operator")
        assert result["actor_id"] == repeat["actor_id"]
        actor_id, membership_id, assignment_id = UUID(result["actor_id"]), UUID(result["membership_id"]), UUID(result["assignment_id"])
        authz = SQLAlchemyAuthorizationAdapter(factory)
        authz.require(actor_id=actor_id, tenant_id=tenant_id, permission=Permission.VIEW_DECISION_WORK_QUEUE, resource_id=tenant_id)
        with factory() as session:
            assert len(session.scalars(select(ExternalIdentityMappingModel).where(ExternalIdentityMappingModel.subject == subject)).all()) == 1
            assert len(session.scalars(select(AuthorizationAdminAuditModel).where(AuthorizationAdminAuditModel.actor_id == actor_id)).all()) == 2
        service.revoke_assignment(assignment_id=assignment_id, operator="deployment-operator")
        with pytest.raises(AuthorizationDenied):
            authz.require(actor_id=actor_id, tenant_id=tenant_id, permission=Permission.VIEW_DECISION_WORK_QUEUE, resource_id=tenant_id)
        service.revoke_membership(membership_id=membership_id, operator="deployment-operator")
        with factory() as session:
            assert len(session.scalars(select(AuthorizationAdminAuditModel).where(AuthorizationAdminAuditModel.actor_id == actor_id)).all()) == 4
    finally:
        engine.dispose()


def test_postgres_provisioning_rejects_identity_reassignment():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    tenant_id, other_tenant_id = uuid4(), uuid4()
    issuer, subject, tenant_key = "https://issuer.example", f"sub-{uuid4()}", f"tenant-{uuid4()}"
    try:
        with factory() as session:
            session.add_all([TenantModel(id=tenant_id, name=f"tenant-{tenant_id}"), TenantModel(id=other_tenant_id, name=f"tenant-{other_tenant_id}")])
            session.commit()
        service = SQLAlchemyAuthorizationProvisioner(factory)
        plan = service.plan_provision(issuer=issuer, subject=subject, tenant_key=tenant_key, tenant_id=tenant_id, role_key="read_only_reviewer")
        service.apply_provision(plan=plan, operator="deployment-operator")
        with pytest.raises(ProvisioningError, match="conflicting"):
            service.plan_provision(issuer=issuer, subject=subject, tenant_key=tenant_key, tenant_id=other_tenant_id, role_key="read_only_reviewer")
    finally:
        engine.dispose()
