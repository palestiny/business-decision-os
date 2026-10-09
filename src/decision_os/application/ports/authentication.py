"""Authentication boundary for HTTP-facing adapters."""
from dataclasses import dataclass
from uuid import UUID


class AuthenticationRequired(PermissionError):
    """Raised when no authenticated principal is available."""


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    actor_id: UUID
    tenant_id: UUID
