from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from decision_os.infrastructure.persistence import models  # noqa: F401
from decision_os.infrastructure.persistence.base import Base
from decision_os.infrastructure.persistence.models.authorization import ActorModel, RoleModel, TenantMembershipModel
from decision_os.infrastructure.persistence.models.authorization_admin_audit import AuthorizationAdminAuditModel
from decision_os.infrastructure.persistence.models.external_identity import ExternalIdentityMappingModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.provisioning import ProvisioningError, SQLAlchemyAuthorizationProvisioner


def _setup():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    tenant_id, role_id = uuid4(), uuid4()
    with factory() as session:
        session.add_all([
            TenantModel(id=tenant_id, name="Test tenant"),
            RoleModel(id=role_id, key="decision_author", name="Decision Author", is_active=True),
        ])
        session.commit()
    return engine, factory, tenant_id


def test_provisioning_dry_run_is_non_mutating_and_apply_is_audited_and_idempotent():
    engine, factory, tenant_id = _setup()
    service = SQLAlchemyAuthorizationProvisioner(factory)
    try:
        plan = service.plan_provision(
            issuer="https://issuer.example", subject="user-123", tenant_key="tenant-a",
            tenant_id=tenant_id, role_key="decision_author",
        )
        with factory() as session:
            assert session.scalar(select(ActorModel.id)) is None
            assert session.scalar(select(ExternalIdentityMappingModel.id)) is None
            assert session.scalar(select(AuthorizationAdminAuditModel.id)) is None

        result = service.apply_provision(plan=plan, operator="operator:deployment")
        repeated_plan = service.plan_provision(
            issuer="https://issuer.example", subject="user-123", tenant_key="tenant-a",
            tenant_id=tenant_id, role_key="decision_author",
        )
        repeated = service.apply_provision(plan=repeated_plan, operator="operator:deployment")
        assert result["actor_id"] == repeated["actor_id"]
        with factory() as session:
            assert len(session.scalars(select(ExternalIdentityMappingModel)).all()) == 1
            assert len(session.scalars(select(TenantMembershipModel)).all()) == 1
            assert len(session.scalars(select(AuthorizationAdminAuditModel)).all()) == 2
    finally:
        engine.dispose()


def test_provisioning_rejects_conflicting_identity_mapping_and_unknown_tenant_or_role():
    engine, factory, tenant_id = _setup()
    service = SQLAlchemyAuthorizationProvisioner(factory)
    try:
        plan = service.plan_provision(
            issuer="https://issuer.example", subject="same-subject", tenant_key="tenant-a",
            tenant_id=tenant_id, role_key="decision_author",
        )
        service.apply_provision(plan=plan, operator="operator:deployment")
        other_tenant_id = uuid4()
        with factory() as session:
            session.add(TenantModel(id=other_tenant_id, name="Other tenant"))
            session.commit()
        with pytest.raises(ProvisioningError, match="conflicting"):
            service.plan_provision(
                issuer="https://issuer.example", subject="same-subject", tenant_key="tenant-a",
                tenant_id=other_tenant_id, role_key="decision_author",
            )
        with pytest.raises(ProvisioningError, match="does not exist"):
            service.plan_provision(
                issuer="https://issuer.example", subject="other", tenant_key="tenant-a",
                tenant_id=uuid4(), role_key="decision_author",
            )
        with pytest.raises(ProvisioningError, match="role"):
            service.plan_provision(
                issuer="https://issuer.example", subject="other", tenant_key="tenant-a",
                tenant_id=tenant_id, role_key="unknown",
            )
    finally:
        engine.dispose()


def test_revoke_membership_and_role_assignment_take_effect_and_are_audited():
    engine, factory, tenant_id = _setup()
    service = SQLAlchemyAuthorizationProvisioner(factory)
    try:
        plan = service.plan_provision(
            issuer="https://issuer.example", subject="user", tenant_key="tenant-a",
            tenant_id=tenant_id, role_key="decision_author",
        )
        result = service.apply_provision(plan=plan, operator="operator:deployment")
        assignment_id = UUID(result["assignment_id"])
        service.revoke_assignment(assignment_id=assignment_id, operator="operator:deployment")
        with factory() as session:
            assignment = session.get(models.MembershipRoleAssignmentModel, assignment_id)
            assert assignment is not None and assignment.is_active is False
            assert len(session.scalars(select(AuthorizationAdminAuditModel)).all()) == 2
        membership_id = UUID(result["membership_id"])
        service.revoke_membership(membership_id=membership_id, operator="operator:deployment")
        with factory() as session:
            membership = session.get(TenantMembershipModel, membership_id)
            assert membership is not None and membership.is_active is False
            assert len(session.scalars(select(AuthorizationAdminAuditModel)).all()) == 3
    finally:
        engine.dispose()


def test_explicit_actor_link_requires_existing_active_actor():
    engine, factory, tenant_id = _setup()
    service = SQLAlchemyAuthorizationProvisioner(factory)
    try:
        with pytest.raises(ProvisioningError, match="existing active actor"):
            service.plan_provision(
                issuer="https://issuer.example", subject="user", tenant_key="tenant-a",
                tenant_id=tenant_id, role_key="decision_author", actor_id=uuid4(),
            )
        with factory() as session:
            actor = ActorModel(is_active=True)
            session.add(actor)
            session.commit()
            actor_id = actor.id
        plan = service.plan_provision(
            issuer="https://issuer.example", subject="user", tenant_key="tenant-a",
            tenant_id=tenant_id, role_key="decision_author", actor_id=actor_id,
        )
        result = service.apply_provision(plan=plan, operator="operator:deployment")
        assert result["actor_id"] == str(actor_id)
    finally:
        engine.dispose()


def test_provisioning_rolls_back_grant_when_audit_write_fails():
    engine, factory, tenant_id = _setup()
    service = SQLAlchemyAuthorizationProvisioner(factory)

    def fail_audit(session, flush_context, instances):
        if any(isinstance(obj, AuthorizationAdminAuditModel) for obj in session.new):
            raise RuntimeError("audit storage unavailable")

    plan = service.plan_provision(
        issuer="https://issuer.example", subject="rollback-user", tenant_key="tenant-a",
        tenant_id=tenant_id, role_key="decision_author",
    )
    event.listen(Session, "before_flush", fail_audit)
    try:
        with pytest.raises(RuntimeError, match="audit storage unavailable"):
            service.apply_provision(plan=plan, operator="operator:deployment")
        with factory() as session:
            assert session.scalar(select(ActorModel.id)) is None
            assert session.scalar(select(ExternalIdentityMappingModel.id)) is None
            assert session.scalar(select(TenantMembershipModel.id)) is None
            assert session.scalar(select(AuthorizationAdminAuditModel.id)) is None
    finally:
        event.remove(Session, "before_flush", fail_audit)
        engine.dispose()



def test_show_identity_reports_effective_permissions_and_denies_unknown_identity():
    engine, factory, tenant_id = _setup()
    service = SQLAlchemyAuthorizationProvisioner(factory)
    try:
        with pytest.raises(ProvisioningError, match="does not exist"):
            service.show_identity(
                issuer="https://issuer.example", subject="missing", tenant_key="tenant-a",
            )
        plan = service.plan_provision(
            issuer="https://issuer.example", subject="viewer", tenant_key="tenant-a",
            tenant_id=tenant_id, role_key="decision_author",
        )
        service.apply_provision(plan=plan, operator="operator:deployment")
        result = service.show_identity(
            issuer="https://issuer.example", subject="viewer", tenant_key="tenant-a",
        )
        assert result["mapping_active"] is True
        assert result["membership_active"] is True
        assert "CREATE_CASE" in result["effective_permissions"]
        assert "APPROVE_DECISION" not in result["effective_permissions"]
    finally:
        engine.dispose()
