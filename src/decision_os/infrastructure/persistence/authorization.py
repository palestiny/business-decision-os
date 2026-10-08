"""Fail-closed SQLAlchemy adapter for tenant-scoped role-based authorization."""
import logging
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

logger = logging.getLogger(__name__)


class SQLAlchemyAuthorizationAdapter(AuthorizationPort):
    """Evaluate permissions against active actor, membership, assignment and role rows.

    The adapter deliberately does not cache decisions: membership or role revocation
    takes effect on the next authorization query.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def require(
        self, *, actor_id: UUID, tenant_id: UUID, permission: Permission, resource_id: UUID
    ) -> None:
        try:
            with self._session_factory() as session:
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
        except SQLAlchemyError as exc:
            logger.exception("Authorization policy store unavailable")
            raise PolicyEvaluationUnavailable("authorization policy store unavailable") from exc

        if granted is None:
            logger.warning(
                "Authorization denied actor_id=%s tenant_id=%s permission=%s resource_id=%s",
                actor_id,
                tenant_id,
                permission.value,
                resource_id,
            )
            raise AuthorizationDenied("required permission is not granted")
