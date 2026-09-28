"""Decision case HTTP routes."""
from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from decision_os.application.api.dependencies import get_principal
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.application.reliability import CreateDecisionCaseReliabilityBoundary
from decision_os.application.commands.create_decision_case import CreateDecisionCaseCommand


@dataclass(frozen=True)
class CreateDecisionCaseRequest:
    case_type: str
    title: str
    case_id: UUID | None = None


def build_router(
    *,
    boundary: CreateDecisionCaseReliabilityBoundary,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.post("/decision-cases", status_code=201)
    def create_decision_case(
        body: CreateDecisionCaseRequest,
        request: Request,
        principal: AuthenticatedPrincipal = Depends(get_principal),
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
        return {
            "data": {
                "id": str(case.id),
                "tenant_id": str(case.tenant_id),
                "case_type": case.case_type,
                "title": case.title,
                "status": case.status.value,
                "version": case.version,
            },
            "correlation_id": str(request.state.correlation_id),
        }

    return router
