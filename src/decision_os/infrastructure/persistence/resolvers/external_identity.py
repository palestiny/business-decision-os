"""SQLAlchemy resolver for pre-provisioned external identity mappings."""
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from decision_os.infrastructure.authentication.oidc_jwt import ExternalIdentity, ExternalIdentityResolver, InternalIdentity
from decision_os.infrastructure.persistence.models.external_identity import ExternalIdentityMappingModel


class SQLAlchemyExternalIdentityResolver(ExternalIdentityResolver):
    """Resolve only active, server-provisioned identity mappings."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def resolve(self, identity: ExternalIdentity) -> InternalIdentity | None:
        with self._session_factory() as session:
            mapping = session.scalar(
                select(ExternalIdentityMappingModel).where(
                    ExternalIdentityMappingModel.issuer == identity.issuer,
                    ExternalIdentityMappingModel.subject == identity.subject,
                    ExternalIdentityMappingModel.tenant_key == identity.tenant_key,
                    ExternalIdentityMappingModel.is_active.is_(True),
                )
            )
            if mapping is None:
                return None
            return InternalIdentity(actor_id=mapping.actor_id, tenant_id=mapping.tenant_id)
