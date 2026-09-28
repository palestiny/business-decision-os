"""FastAPI application factory."""
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from decision_os.application.api.errors import (
    authentication_required_handler,
    authorization_denied_handler,
    domain_error_handler,
    error_payload,
    idempotency_conflict_handler,
    policy_unavailable_handler,
    request_in_progress_handler,
    unexpected_error_handler,
)
from decision_os.application.api.routes import build_router
from decision_os.application.api.dependencies import PrincipalProvider, get_principal
from decision_os.application.ports.authentication import AuthenticationRequired
from decision_os.application.ports.authority import AuthorizationDenied, PolicyEvaluationUnavailable
from decision_os.application.ports.idempotency import IdempotencyConflict, RequestInProgress
from decision_os.domain.decision_case import DomainError
from decision_os.domain.decision import DecisionError


def create_app(*, create_case_boundary, triage_case_boundary=None, make_decision_boundary=None, principal_provider: PrincipalProvider = get_principal) -> FastAPI:
    app = FastAPI(title="Business Decision OS API", version="0.1.0")

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        supplied = request.headers.get("X-Correlation-ID")
        if supplied:
            try:
                correlation_id = UUID(supplied)
            except ValueError:
                correlation_id = uuid4()
                request.state.correlation_id = correlation_id
                return JSONResponse(
                    status_code=422,
                    content=error_payload(
                        "VALIDATION_ERROR",
                        "The X-Correlation-ID header must be a UUID.",
                        str(correlation_id),
                    ),
                )
        else:
            correlation_id = uuid4()
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = str(correlation_id)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_payload(
                "VALIDATION_ERROR",
                "The request is invalid.",
                str(request.state.correlation_id),
            ),
        )

    app.add_exception_handler(AuthenticationRequired, authentication_required_handler)
    app.add_exception_handler(AuthorizationDenied, authorization_denied_handler)
    app.add_exception_handler(IdempotencyConflict, idempotency_conflict_handler)
    app.add_exception_handler(RequestInProgress, request_in_progress_handler)
    app.add_exception_handler(PolicyEvaluationUnavailable, policy_unavailable_handler)
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(DecisionError, domain_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)

    app.include_router(
        build_router(
            boundary=create_case_boundary,
            triage_boundary=triage_case_boundary,
            make_decision_boundary=make_decision_boundary,
            principal_provider=principal_provider,
        )
    )
    return app
