"""Fail-closed SQLAlchemy RBAC adapter with durable allow/deny audit."""
import logging
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from decision_os.application.ports.authority import (
    AuthorizationDenied,
    AuthorizationPort,
    Permission,
    PolicyEvaluationUnavailable,
)
from decision_os.infrastructure.persistence.models.authorization import (
    ActorModel,
    MembershipRoleAssignmentModel,
    RoleModel,
    RolePermissionModel,
    TenantMembershipModel,
)
from decision_os.infrastructure.persistence.models.authorization_decision_audit import AuthorizationDecisionAuditModel

logger = logging.getLogger(__name__)


class SQLAlchemyAuthorizationAdapter(AuthorizationPort):
    """Evaluate current RBAC state and commit a durable audit before returning.

    No decision is cached. If policy evaluation or audit persistence fails, the
    request fails closed. Audit rows contain identifiers and bounded policy
    metadata only, never credentials or token claims.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def require(
        self, *, actor_id: UUID, tenant_id: UUID, permission: Permission,
        resource_id: UUID, correlation_id: UUID | None = None,
    ) -> None:
        allowed = False
        try:
            with self._session_factory() as session:
                with session.begin():
                    granted = session.scalar(
                        select(ActorModel.id)
                        .join(TenantMembershipModel, TenantMembershipModel.actor_id == ActorModel.id)
                        .join(
                            MembershipRoleAssignmentModel,
                            MembershipRoleAssignmentModel.membership_id == TenantMembershipModel.id,
                        )
                        .join(RoleModel, RoleModel.id == MembershipRoleAssignmentModel.role_id)
                        .join(RolePermissionModel, RolePermissionModel.role_id == RoleModel.id)
                        .where(
                            ActorModel.id == actor_id,
                            ActorModel.is_active.is_(True),
                            TenantMembershipModel.tenant_id == tenant_id,
                            TenantMembershipModel.is_active.is_(True),
                            MembershipRoleAssignmentModel.is_active.is_(True),
                            RoleModel.is_active.is_(True),
                            RolePermissionModel.permission == permission.value,
                        )
                        .limit(1)
                    )
                    allowed = granted is not None
                    session.add(AuthorizationDecisionAuditModel(
                        actor_id=actor_id,
                        tenant_id=tenant_id,
                        permission=permission.value,
                        resource_id=resource_id,
                        outcome="ALLOW" if allowed else "DENY",
                        reason_code="PERMISSION_GRANTED" if allowed else "PERMISSION_NOT_GRANTED",
                        occurred_at=datetime.now(timezone.utc),
                        correlation_id=correlation_id,
                    ))
        except SQLAlchemyError as exc:
            logger.exception(
                "Authorization decision or audit persistence failed actor_id=%s tenant_id=%s permission=%s",
                actor_id, tenant_id, permission.value,
            )
            raise PolicyEvaluationUnavailable("authorization decision could not be durably evaluated") from exc

        if not allowed:
            logger.warning(
                "Authorization denied actor_id=%s tenant_id=%s permission=%s resource_id=%s",
                actor_id, tenant_id, permission.value, resource_id,
            )
            raise AuthorizationDenied("required permission is not granted")
