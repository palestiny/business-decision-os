"""Decision case HTTP routes."""
from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from decision_os.application.api.dependencies import PrincipalProvider, get_principal
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.application.reliability import CreateDecisionCaseReliabilityBoundary
from decision_os.application.triage_reliability import TriageCaseReliabilityBoundary
from decision_os.application.commands.create_decision_case import CreateDecisionCaseCommand
from decision_os.application.commands.triage_case import TriageCaseCommand


@dataclass(frozen=True)
class CreateDecisionCaseRequest:
    case_type: str
    title: str
    case_id: UUID | None = None


def _case_response(case, correlation_id: UUID) -> dict[str, object]:
    return {
        "data": {
            "id": str(case.id),
            "tenant_id": str(case.tenant_id),
            "case_type": case.case_type,
            "title": case.title,
            "status": case.status.value,
            "version": case.version,
        },
        "correlation_id": str(correlation_id),
    }


def build_router(
    *,
    boundary: CreateDecisionCaseReliabilityBoundary,
    triage_boundary: TriageCaseReliabilityBoundary | None = None,
    principal_provider: PrincipalProvider = get_principal,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.post("/decision-cases", status_code=201)
    def create_decision_case(
        body: CreateDecisionCaseRequest,
        request: Request,
        principal: AuthenticatedPrincipal = Depends(principal_provider),
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
    ) -> dict[str, object]:
        case = boundary.execute(
            CreateDecisionCaseCommand(
                tenant_id=principal.tenant_id,
                actor_id=principal.actor_id,
                case_type=body.case_type,
                title=body.title,
                case_id=body.case_id,
            ),
            idempotency_key=idempotency_key,
            correlation_id=request.state.correlation_id,
        )
        return _case_response(case, request.state.correlation_id)

    if triage_boundary is not None:
        @router.post("/decision-cases/{case_id}/triage", status_code=200)
        def triage_decision_case(
            case_id: UUID,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            case = triage_boundary.execute(
                TriageCaseCommand(
                    tenant_id=principal.tenant_id,
                    actor_id=principal.actor_id,
                    case_id=case_id,
                ),
                idempotency_key=idempotency_key,
                correlation_id=request.state.correlation_id,
            )
            return _case_response(case, request.state.correlation_id)

    return router
