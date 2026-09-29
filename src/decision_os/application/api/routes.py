"""Decision case HTTP routes."""
from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from decision_os.application.api.dependencies import PrincipalProvider, get_principal
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.application.reliability import CreateDecisionCaseReliabilityBoundary
from decision_os.application.triage_reliability import TriageCaseReliabilityBoundary
from decision_os.application.make_decision_reliability import MakeDecisionReliabilityBoundary
from decision_os.application.approve_decision_reliability import ApproveDecisionReliabilityBoundary
from decision_os.application.reject_decision_reliability import RejectDecisionReliabilityBoundary
from decision_os.application.start_analysis_reliability import StartAnalysisReliabilityBoundary
from decision_os.application.commands.create_decision_case import CreateDecisionCaseCommand
from decision_os.application.commands.triage_case import TriageCaseCommand
from decision_os.application.commands.make_decision import MakeDecisionCommand
from decision_os.application.commands.approve_decision import ApproveDecisionCommand
from decision_os.application.commands.reject_decision import RejectDecisionCommand
from decision_os.application.commands.start_analysis import StartAnalysisCommand


@dataclass(frozen=True)
class CreateDecisionCaseRequest:
    case_type: str
    title: str
    case_id: UUID | None = None


@dataclass(frozen=True)
class MakeDecisionRequest:
    decision_id: UUID
    option_ids: tuple[UUID, ...]
    rationale: str


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


def _decision_response(decision, correlation_id: UUID) -> dict[str, object]:
    return {
        "data": {
            "id": str(decision.id),
            "case_id": str(decision.case_id),
            "selected_option_ids": [str(value) for value in decision.selected_option_ids],
            "rationale": decision.rationale,
            "status": decision.status.value,
            "decided_by": str(decision.decided_by),
            "approval_required": decision.approval_required,
            "policy_ids": [str(value) for value in decision.policy_ids],
        },
        "correlation_id": str(correlation_id),
    }


def build_router(
    *,
    boundary: CreateDecisionCaseReliabilityBoundary,
    triage_boundary: TriageCaseReliabilityBoundary | None = None,
    make_decision_boundary: MakeDecisionReliabilityBoundary | None = None,
    approve_decision_boundary: ApproveDecisionReliabilityBoundary | None = None,
    reject_decision_boundary: RejectDecisionReliabilityBoundary | None = None,
    start_analysis_boundary: StartAnalysisReliabilityBoundary | None = None,
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

    if make_decision_boundary is not None:
        @router.post("/decision-cases/{case_id}/decision", status_code=200)
        def make_decision(
            case_id: UUID,
            body: MakeDecisionRequest,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            decision = make_decision_boundary.execute(
                MakeDecisionCommand(
                    tenant_id=principal.tenant_id,
                    actor_id=principal.actor_id,
                    case_id=case_id,
                    decision_id=body.decision_id,
                    option_ids=body.option_ids,
                    rationale=body.rationale,
                ),
                idempotency_key=idempotency_key,
                correlation_id=request.state.correlation_id,
            )
            return _decision_response(decision, request.state.correlation_id)

    if approve_decision_boundary is not None:
        @router.post("/decision-cases/{case_id}/decision/{decision_id}/approve", status_code=200)
        def approve_decision(
            case_id: UUID,
            decision_id: UUID,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            decision = approve_decision_boundary.execute(
                ApproveDecisionCommand(
                    tenant_id=principal.tenant_id,
                    actor_id=principal.actor_id,
                    case_id=case_id,
                    decision_id=decision_id,
                ),
                idempotency_key=idempotency_key,
                correlation_id=request.state.correlation_id,
            )
            return _decision_response(decision, request.state.correlation_id)

    if reject_decision_boundary is not None:
        @router.post("/decision-cases/{case_id}/decision/{decision_id}/reject", status_code=200)
        def reject_decision(
            case_id: UUID,
            decision_id: UUID,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            decision = reject_decision_boundary.execute(
                RejectDecisionCommand(
                    tenant_id=principal.tenant_id,
                    actor_id=principal.actor_id,
                    case_id=case_id,
                    decision_id=decision_id,
                ),
                idempotency_key=idempotency_key,
                correlation_id=request.state.correlation_id,
            )
            return _decision_response(decision, request.state.correlation_id)

    if start_analysis_boundary is not None:
        @router.post("/decision-cases/{case_id}/analysis/start", status_code=200)
        def start_analysis(
            case_id: UUID,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            case = start_analysis_boundary.execute(
                StartAnalysisCommand(
                    tenant_id=principal.tenant_id,
                    actor_id=principal.actor_id,
                    case_id=case_id,
                ),
                idempotency_key=idempotency_key,
                correlation_id=request.state.correlation_id,
            )
            return _case_response(case, request.state.correlation_id)

    return router
