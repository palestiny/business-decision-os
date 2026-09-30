"""Decision case HTTP routes."""
from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from decision_os.application.api.dependencies import PrincipalProvider, get_principal
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.application.reliability import CreateDecisionCaseReliabilityBoundary
from decision_os.application.create_action_reliability import CreateActionReliabilityBoundary
from decision_os.application.start_action_reliability import StartActionReliabilityBoundary
from decision_os.application.complete_action_execution_reliability import CompleteActionExecutionReliabilityBoundary
from decision_os.application.reconcile_unknown_execution_reliability import ReconcileUnknownExecutionReliabilityBoundary
from decision_os.application.mark_execution_unknown_reliability import MarkExecutionUnknownReliabilityBoundary
from decision_os.application.commands.mark_execution_unknown import MarkExecutionUnknownCommand
from decision_os.application.commands.complete_action_execution import CompleteActionExecutionCommand
from decision_os.application.commands.reconcile_unknown_execution import ReconcileUnknownExecutionCommand
from decision_os.domain.action import ActionExecutionStatus
from decision_os.application.submit_options_reliability import SubmitOptionsReliabilityBoundary
from decision_os.application.await_decision_reliability import AwaitDecisionReliabilityBoundary
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
from decision_os.application.commands.submit_options import SubmitOptionsCommand
from decision_os.application.commands.await_decision import AwaitDecisionCommand
from decision_os.application.commands.create_action import CreateActionCommand
from decision_os.application.commands.start_action import StartActionCommand


@dataclass(frozen=True)
class CreateDecisionCaseRequest:
    case_type: str
    title: str
    case_id: UUID | None = None


@dataclass(frozen=True)
class DecisionOptionRequest:
    id: UUID
    title: str


@dataclass(frozen=True)
class CreateActionRequest:
    decision_id: UUID
    action_type: str
    parameters: str = ""
    action_id: UUID | None = None


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
    submit_options_boundary: SubmitOptionsReliabilityBoundary | None = None,
    await_decision_boundary: AwaitDecisionReliabilityBoundary | None = None,
    create_action_boundary: CreateActionReliabilityBoundary | None = None,
    start_action_boundary: StartActionReliabilityBoundary | None = None,
    complete_execution_boundary: CompleteActionExecutionReliabilityBoundary | None = None,
    reconcile_execution_boundary: ReconcileUnknownExecutionReliabilityBoundary | None = None,
    mark_unknown_execution_boundary: MarkExecutionUnknownReliabilityBoundary | None = None,
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

    if submit_options_boundary is not None:
        @router.post("/decision-cases/{case_id}/options", status_code=200)
        def submit_options(
            case_id: UUID,
            body: tuple[DecisionOptionRequest, ...],
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            result = submit_options_boundary.execute(
                SubmitOptionsCommand(
                    tenant_id=principal.tenant_id,
                    actor_id=principal.actor_id,
                    case_id=case_id,
                    options=tuple((item.id, item.title) for item in body),
                ),
                idempotency_key=idempotency_key,
                correlation_id=request.state.correlation_id,
            )
            return {
                "data": {
                    "case_id": str(result.case_id),
                    "options": [{"id": str(option.id), "case_id": str(option.case_id), "title": option.title} for option in result.options],
                    "status": result.status,
                    "version": result.version,
                },
                "correlation_id": str(request.state.correlation_id),
            }

    if await_decision_boundary is not None:
        @router.post("/decision-cases/{case_id}/decision/await", status_code=200)
        def await_decision(
            case_id: UUID,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            case = await_decision_boundary.execute(
                AwaitDecisionCommand(tenant_id=principal.tenant_id, actor_id=principal.actor_id, case_id=case_id),
                idempotency_key=idempotency_key,
                correlation_id=request.state.correlation_id,
            )
            return _case_response(case, request.state.correlation_id)

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


    if create_action_boundary is not None:
        @router.post("/decision-cases/{case_id}/actions", status_code=201)
        def create_action(
            case_id: UUID,
            body: CreateActionRequest,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            action = create_action_boundary.execute(
                CreateActionCommand(
                    tenant_id=principal.tenant_id, actor_id=principal.actor_id,
                    case_id=case_id, decision_id=body.decision_id,
                    action_type=body.action_type, parameters=body.parameters,
                    action_id=body.action_id,
                ),
                idempotency_key=idempotency_key, correlation_id=request.state.correlation_id,
            )
            return {
                "data": {
                    "id": str(action.id), "tenant_id": str(action.tenant_id),
                    "case_id": str(action.case_id), "decision_id": str(action.decision_id),
                    "action_type": action.action_type, "parameters": action.parameters,
                    "status": action.status.value, "version": action.version,
                },
                "correlation_id": str(request.state.correlation_id),
            }

    if start_action_boundary is not None:
        @router.post("/actions/{action_id}/start", status_code=200)
        def start_action(
            action_id: UUID,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            execution = start_action_boundary.execute(
                StartActionCommand(
                    tenant_id=principal.tenant_id, actor_id=principal.actor_id,
                    action_id=action_id,
                ),
                idempotency_key=idempotency_key, correlation_id=request.state.correlation_id,
            )
            return {
                "data": {
                    "id": str(execution.id), "action_id": str(execution.action_id),
                    "attempt": execution.attempt, "status": execution.status.value,
                },
                "correlation_id": str(request.state.correlation_id),
            }

    if complete_execution_boundary is not None:
        @router.post("/action-executions/{execution_id}/complete", status_code=200)
        def complete_action_execution(
            execution_id: UUID,
            outcome: ActionExecutionStatus,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            execution = complete_execution_boundary.execute(
                CompleteActionExecutionCommand(
                    tenant_id=principal.tenant_id, actor_id=principal.actor_id,
                    execution_id=execution_id, outcome=outcome,
                ),
                idempotency_key=idempotency_key, correlation_id=request.state.correlation_id,
            )
            return {
                "data": {"id": str(execution.id), "action_id": str(execution.action_id), "attempt": execution.attempt, "status": execution.status.value},
                "correlation_id": str(request.state.correlation_id),
            }

    if reconcile_execution_boundary is not None:
        @router.post("/action-executions/{execution_id}/reconcile", status_code=200)
        def reconcile_unknown_execution(
            execution_id: UUID,
            observed_outcome: ActionExecutionStatus,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            execution = reconcile_execution_boundary.execute(
                ReconcileUnknownExecutionCommand(
                    tenant_id=principal.tenant_id, actor_id=principal.actor_id,
                    execution_id=execution_id, observed_outcome=observed_outcome,
                ),
                idempotency_key=idempotency_key, correlation_id=request.state.correlation_id,
            )
            return {
                "data": {"id": str(execution.id), "action_id": str(execution.action_id), "attempt": execution.attempt, "status": execution.status.value},
                "correlation_id": str(request.state.correlation_id),
            }


    if mark_unknown_execution_boundary is not None:
        @router.post("/action-executions/{execution_id}/unknown", status_code=200)
        def mark_execution_unknown(
            execution_id: UUID,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
            idempotency_key: str = Header(..., alias="Idempotency-Key"),
        ) -> dict[str, object]:
            execution = mark_unknown_execution_boundary.execute(
                MarkExecutionUnknownCommand(
                    tenant_id=principal.tenant_id, actor_id=principal.actor_id,
                    execution_id=execution_id,
                ),
                idempotency_key=idempotency_key, correlation_id=request.state.correlation_id,
            )
            return {
                "data": {"id": str(execution.id), "action_id": str(execution.action_id), "attempt": execution.attempt, "status": execution.status.value},
                "correlation_id": str(request.state.correlation_id),
            }


    return router
