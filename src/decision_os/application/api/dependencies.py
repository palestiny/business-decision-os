"""FastAPI dependencies for request identity."""
from fastapi import Request

from decision_os.application.ports.authentication import (
    AuthenticatedPrincipal,
    AuthenticationRequired,
)


def get_principal(request: Request) -> AuthenticatedPrincipal:
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise AuthenticationRequired("authenticated principal required")
    return principal
