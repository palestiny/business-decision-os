"""FastAPI application factory."""
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from decision_os.application.api.errors import (
    authentication_required_handler, authorization_denied_handler, concurrency_conflict_handler,
    domain_error_handler, error_payload, idempotency_conflict_handler, invalid_action_handler,
    policy_unavailable_handler, request_in_progress_handler, unexpected_error_handler,
)
from decision_os.application.api.routes import build_router
from decision_os.application.api.dependencies import PrincipalProvider, get_principal
from decision_os.application.ports.authentication import AuthenticationRequired
from decision_os.application.ports.decision_memory import DecisionMemoryReader
from decision_os.application.ports.decision_work_queue import DecisionWorkQueueReader
from decision_os.application.ports.authority import AuthorizationDenied, PolicyEvaluationUnavailable
from decision_os.application.ports.idempotency import IdempotencyConflict, RequestInProgress
from decision_os.application.ports.reliability import ConcurrencyConflict
from decision_os.domain.decision_case import DomainError
from decision_os.domain.decision import DecisionError
from decision_os.domain.action import InvalidAction


def create_app(*, create_case_boundary, triage_case_boundary=None, make_decision_boundary=None, approve_decision_boundary=None, reject_decision_boundary=None, start_analysis_boundary=None, submit_options_boundary=None, await_decision_boundary=None, create_action_boundary=None, start_action_boundary=None, complete_execution_boundary=None, reconcile_execution_boundary=None, mark_unknown_execution_boundary=None, create_expected_outcome_boundary=None, record_actual_outcome_boundary=None, verify_outcome_boundary=None, create_evidence_boundary=None, add_analysis_finding_boundary=None, decision_memory_reader: DecisionMemoryReader | None = None, decision_work_queue_reader: DecisionWorkQueueReader | None = None, principal_provider: PrincipalProvider = get_principal) -> FastAPI:
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
                return JSONResponse(status_code=422, content=error_payload("VALIDATION_ERROR", "The X-Correlation-ID header must be a UUID.", str(correlation_id)))
        else:
            correlation_id = uuid4()
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = str(correlation_id)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content=error_payload("VALIDATION_ERROR", "The request is invalid.", str(request.state.correlation_id)))

    app.add_exception_handler(AuthenticationRequired, authentication_required_handler)
    app.add_exception_handler(AuthorizationDenied, authorization_denied_handler)
    app.add_exception_handler(IdempotencyConflict, idempotency_conflict_handler)
    app.add_exception_handler(RequestInProgress, request_in_progress_handler)
    app.add_exception_handler(ConcurrencyConflict, concurrency_conflict_handler)
    app.add_exception_handler(PolicyEvaluationUnavailable, policy_unavailable_handler)
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(DecisionError, domain_error_handler)
    app.add_exception_handler(InvalidAction, invalid_action_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)

    app.include_router(build_router(
        boundary=create_case_boundary, triage_boundary=triage_case_boundary, make_decision_boundary=make_decision_boundary,
        approve_decision_boundary=approve_decision_boundary, reject_decision_boundary=reject_decision_boundary,
        start_analysis_boundary=start_analysis_boundary, submit_options_boundary=submit_options_boundary,
        await_decision_boundary=await_decision_boundary, create_action_boundary=create_action_boundary,
        start_action_boundary=start_action_boundary, complete_execution_boundary=complete_execution_boundary,
        reconcile_execution_boundary=reconcile_execution_boundary, mark_unknown_execution_boundary=mark_unknown_execution_boundary,
        create_expected_outcome_boundary=create_expected_outcome_boundary, record_actual_outcome_boundary=record_actual_outcome_boundary,
        verify_outcome_boundary=verify_outcome_boundary, create_evidence_boundary=create_evidence_boundary,
        add_analysis_finding_boundary=add_analysis_finding_boundary, decision_memory_reader=decision_memory_reader, decision_work_queue_reader=decision_work_queue_reader, principal_provider=principal_provider,
    ))
    return app
