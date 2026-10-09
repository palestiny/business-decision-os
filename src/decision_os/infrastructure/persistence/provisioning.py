"""Trusted, offline provisioning operations for tenant-scoped RBAC.

This module is intentionally not mounted on the public HTTP API. Operators must
invoke the dedicated CLI inside a trusted deployment environment.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from decision_os.infrastructure.persistence.models.authorization import (
    ActorModel,
    MembershipRoleAssignmentModel,
    RoleModel,
    TenantMembershipModel,
)
from decision_os.infrastructure.persistence.models.authorization_admin_audit import AuthorizationAdminAuditModel
from decision_os.infrastructure.persistence.models.external_identity import ExternalIdentityMappingModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel


class ProvisioningError(ValueError):
    """A provisioning request conflicts with authoritative state."""


@dataclass(frozen=True)
class ProvisioningPlan:
    issuer: str
    subject: str
    tenant_key: str
    tenant_id: UUID
    role_key: str
    actor_id: UUID
    membership_id: UUID
    role_id: UUID
    mapping_exists: bool
    membership_exists: bool
    assignment_exists: bool
    creates_actor: bool

    def as_dict(self) -> dict:
        return {key: str(value) if isinstance(value, UUID) else value for key, value in asdict(self).items()}


class SQLAlchemyAuthorizationProvisioner:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def plan_provision(
        self, *, issuer: str, subject: str, tenant_key: str, tenant_id: UUID,
        role_key: str, actor_id: UUID | None = None,
    ) -> ProvisioningPlan:
        self._validate_text(issuer, "issuer", 500)
        self._validate_text(subject, "subject", 500)
        self._validate_text(tenant_key, "tenant_key", 255)
        self._validate_text(role_key, "role_key", 80)
        with self._session_factory() as session:
            tenant = session.get(TenantModel, tenant_id)
            if tenant is None:
                raise ProvisioningError("target tenant does not exist")
            role = session.scalar(select(RoleModel).where(RoleModel.key == role_key))
            if role is None or not role.is_active:
                raise ProvisioningError("target role does not exist or is inactive")
            mapping = session.scalar(select(ExternalIdentityMappingModel).where(
                ExternalIdentityMappingModel.issuer == issuer,
                ExternalIdentityMappingModel.subject == subject,
                ExternalIdentityMappingModel.tenant_key == tenant_key,
            ))
            if mapping is not None:
                if not mapping.is_active:
                    raise ProvisioningError("identity mapping exists but is inactive; explicit recovery is required")
                if mapping.tenant_id != tenant_id or (actor_id is not None and mapping.actor_id != actor_id):
                    raise ProvisioningError("identity mapping already exists with conflicting actor or tenant")
                resolved_actor_id = mapping.actor_id
            else:
                resolved_actor_id = actor_id or uuid4()
                actor = session.get(ActorModel, resolved_actor_id)
                if actor_id is not None and (actor is None or not actor.is_active):
                    raise ProvisioningError("explicit actor_id must reference an existing active actor")
                if actor is not None and not actor.is_active:
                    raise ProvisioningError("target actor is inactive")
            actor = session.get(ActorModel, resolved_actor_id)
            if actor is not None and not actor.is_active:
                raise ProvisioningError("target actor is inactive")
            membership = session.scalar(select(TenantMembershipModel).where(
                TenantMembershipModel.actor_id == resolved_actor_id,
                TenantMembershipModel.tenant_id == tenant_id,
            ))
            if membership is not None and not membership.is_active:
                raise ProvisioningError("tenant membership exists but is inactive; explicit recovery is required")
            assignment = None
            if membership is not None:
                assignment = session.scalar(select(MembershipRoleAssignmentModel).where(
                    MembershipRoleAssignmentModel.membership_id == membership.id,
                    MembershipRoleAssignmentModel.role_id == role.id,
                ))
                if assignment is not None and not assignment.is_active:
                    raise ProvisioningError("role assignment exists but is inactive; explicit recovery is required")
            return ProvisioningPlan(
                issuer=issuer, subject=subject, tenant_key=tenant_key, tenant_id=tenant_id,
                role_key=role_key, actor_id=resolved_actor_id,
                membership_id=membership.id if membership else uuid4(), role_id=role.id,
                mapping_exists=mapping is not None, membership_exists=membership is not None,
                assignment_exists=assignment is not None, creates_actor=actor is None,
            )

    def apply_provision(self, *, plan: ProvisioningPlan, operator: str) -> dict:
        self._validate_text(operator, "operator", 200)
        correlation_id = uuid4()
        with self._session_factory() as session:
            with session.begin():
                tenant = session.get(TenantModel, plan.tenant_id)
                role = session.scalar(select(RoleModel).where(RoleModel.id == plan.role_id))
                if tenant is None:
                    raise ProvisioningError("target tenant does not exist")
                if role is None or not role.is_active or role.key != plan.role_key:
                    raise ProvisioningError("target role changed or is inactive")
                mapping = session.scalar(select(ExternalIdentityMappingModel).where(
                    ExternalIdentityMappingModel.issuer == plan.issuer,
                    ExternalIdentityMappingModel.subject == plan.subject,
                    ExternalIdentityMappingModel.tenant_key == plan.tenant_key,
                ))
                if mapping is not None:
                    if not mapping.is_active or mapping.actor_id != plan.actor_id or mapping.tenant_id != plan.tenant_id:
                        raise ProvisioningError("identity mapping changed or conflicts with the plan")
                    actor_id = mapping.actor_id
                else:
                    actor_id = plan.actor_id
                    actor = session.get(ActorModel, actor_id)
                    if plan.creates_actor:
                        if actor is not None:
                            raise ProvisioningError("planned actor ID was created concurrently; re-plan")
                        session.add(ActorModel(id=actor_id, is_active=True))
                    elif actor is None or not actor.is_active:
                        raise ProvisioningError("explicit actor no longer exists or is inactive")
                    session.add(ExternalIdentityMappingModel(
                        issuer=plan.issuer, subject=plan.subject, tenant_key=plan.tenant_key,
                        actor_id=actor_id, tenant_id=plan.tenant_id, is_active=True,
                    ))
                membership = session.scalar(select(TenantMembershipModel).where(
                    TenantMembershipModel.actor_id == actor_id,
                    TenantMembershipModel.tenant_id == plan.tenant_id,
                ))
                if membership is None:
                    membership = TenantMembershipModel(
                        id=plan.membership_id, actor_id=actor_id, tenant_id=plan.tenant_id, is_active=True,
                    )
                    session.add(membership)
                    session.flush()
                elif not membership.is_active:
                    raise ProvisioningError("tenant membership is inactive; explicit recovery is required")
                assignment = session.scalar(select(MembershipRoleAssignmentModel).where(
                    MembershipRoleAssignmentModel.membership_id == membership.id,
                    MembershipRoleAssignmentModel.role_id == role.id,
                ))
                if assignment is None:
                    assignment = MembershipRoleAssignmentModel(
                        membership_id=membership.id, role_id=role.id, is_active=True,
                    )
                    session.add(assignment)
                    session.flush()
                elif not assignment.is_active:
                    raise ProvisioningError("role assignment is inactive; explicit recovery is required")
                audit = AuthorizationAdminAuditModel(
                    operator=operator, operation="PROVISION_IDENTITY_ACCESS",
                    target_type="membership_role_assignment", target_id=assignment.id,
                    actor_id=actor_id, tenant_id=plan.tenant_id, role_key=plan.role_key,
                    occurred_at=datetime.now(timezone.utc), correlation_id=correlation_id,
                    details={
                        "issuer": plan.issuer, "subject": plan.subject, "tenant_key": plan.tenant_key,
                        "mapping_created": mapping is None, "membership_created": not plan.membership_exists,
                        "assignment_created": not plan.assignment_exists,
                    },
                )
                session.add(audit)
                return {
                    "actor_id": str(actor_id), "tenant_id": str(plan.tenant_id),
                    "membership_id": str(membership.id), "role_key": plan.role_key,
                    "assignment_id": str(assignment.id), "correlation_id": str(correlation_id),
                }

    def revoke_membership(self, *, membership_id: UUID, operator: str) -> dict:
        return self._revoke(target_type="membership", target_id=membership_id, operator=operator)

    def revoke_assignment(self, *, assignment_id: UUID, operator: str) -> dict:
        return self._revoke(target_type="role_assignment", target_id=assignment_id, operator=operator)

    def _revoke(self, *, target_type: str, target_id: UUID, operator: str) -> dict:
        self._validate_text(operator, "operator", 200)
        correlation_id = uuid4()
        with self._session_factory() as session:
            with session.begin():
                if target_type == "membership":
                    target = session.get(TenantMembershipModel, target_id)
                else:
                    target = session.get(MembershipRoleAssignmentModel, target_id)
                if target is None:
                    raise ProvisioningError(f"{target_type} does not exist")
                membership = target if target_type == "membership" else session.get(TenantMembershipModel, target.membership_id)
                if membership is None:
                    raise ProvisioningError("role assignment has no membership")
                changed = target.is_active
                target.is_active = False
                assignment = target if target_type == "role_assignment" else None
                if target_type == "membership":
                    tenant_id, actor_id = membership.tenant_id, membership.actor_id
                    role_key = None
                else:
                    tenant_id, actor_id = membership.tenant_id, membership.actor_id
                    role = session.get(RoleModel, target.role_id)
                    role_key = role.key if role else None
                session.add(AuthorizationAdminAuditModel(
                    operator=operator, operation=f"REVOKE_{target_type.upper()}",
                    target_type=target_type, target_id=target_id, actor_id=actor_id,
                    tenant_id=tenant_id, role_key=role_key, occurred_at=datetime.now(timezone.utc),
                    correlation_id=correlation_id, details={"changed": bool(changed)},
                ))
                return {
                    "target_type": target_type, "target_id": str(target_id),
                    "changed": bool(changed), "correlation_id": str(correlation_id),
                }

    @staticmethod
    def _validate_text(value: str, name: str, max_length: int) -> None:
        if not isinstance(value, str) or not value.strip() or len(value) > max_length:
            raise ProvisioningError(f"{name} must be non-empty and at most {max_length} characters")
