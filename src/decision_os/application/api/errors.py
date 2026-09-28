"""HTTP error mapping for application/domain boundaries."""
from fastapi import Request
from fastapi.responses import JSONResponse

from decision_os.application.ports.authority import AuthorizationDenied, PolicyEvaluationUnavailable
from decision_os.application.ports.idempotency import IdempotencyConflict, RequestInProgress
from decision_os.application.ports.authentication import AuthenticationRequired
from decision_os.domain.decision_case import DomainError


def error_payload(code: str, message: str, correlation_id: str) -> dict[str, object]:
    return {
        "error": {
            "code": code,
            "message": message,
        },
        "correlation_id": correlation_id,
    }


def _correlation_id(request: Request) -> str:
    return str(getattr(request.state, "correlation_id"))


async def authentication_required_handler(request: Request, exc: AuthenticationRequired) -> JSONResponse:
    return JSONResponse(status_code=401, content=error_payload("AUTHENTICATION_REQUIRED", "Authentication is required.", _correlation_id(request)))


async def authorization_denied_handler(request: Request, exc: AuthorizationDenied) -> JSONResponse:
    return JSONResponse(status_code=403, content=error_payload("AUTHORIZATION_DENIED", "The actor is not authorized for this operation.", _correlation_id(request)))


async def idempotency_conflict_handler(request: Request, exc: IdempotencyConflict) -> JSONResponse:
    return JSONResponse(status_code=409, content=error_payload("IDEMPOTENCY_CONFLICT", "The idempotency key was already used with a different request.", _correlation_id(request)))


async def request_in_progress_handler(request: Request, exc: RequestInProgress) -> JSONResponse:
    return JSONResponse(status_code=409, content=error_payload("REQUEST_IN_PROGRESS", "A request with this idempotency key is already in progress.", _correlation_id(request)))


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=409, content=error_payload("DOMAIN_CONFLICT", str(exc), _correlation_id(request)))


async def policy_unavailable_handler(request: Request, exc: PolicyEvaluationUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content=error_payload("POLICY_UNAVAILABLE", "Decision policy evaluation is temporarily unavailable.", _correlation_id(request)))


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content=error_payload("INTERNAL_ERROR", "An unexpected error occurred.", _correlation_id(request)))
