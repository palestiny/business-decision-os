"""FastAPI dependencies for request identity."""
from typing import Callable
from uuid import UUID

from fastapi import Request

from decision_os.application.ports.authentication import (
    AuthenticatedPrincipal,
    AuthenticationRequired,
)


PrincipalProvider = Callable[[Request], AuthenticatedPrincipal]


def get_principal(request: Request) -> AuthenticatedPrincipal:
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise AuthenticationRequired("authenticated principal required")
    return principal
