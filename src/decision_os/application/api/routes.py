"""Decision case HTTP routes."""
from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from decision_os.application.api.dependencies import PrincipalProvider, get_principal
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.application.ports.decision_memory import DecisionMemoryReader
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
from decision_os.application.create_expected_outcome_reliability import CreateExpectedOutcomeReliabilityBoundary
from decision_os.application.record_actual_outcome_reliability import RecordActualOutcomeReliabilityBoundary
from decision_os.application.verify_outcome_reliability import VerifyOutcomeReliabilityBoundary
from decision_os.application.create_evidence_reliability import CreateEvidenceReliabilityBoundary
from decision_os.application.add_analysis_finding_reliability import AddAnalysisFindingReliabilityBoundary
from decision_os.application.commands.create_expected_outcome import CreateExpectedOutcomeCommand
from decision_os.application.commands.record_actual_outcome import RecordActualOutcomeCommand
from decision_os.application.commands.verify_outcome import VerifyOutcomeCommand
from decision_os.application.commands.create_evidence import CreateEvidenceCommand
from decision_os.application.commands.add_analysis_finding import AddAnalysisFindingCommand
from decision_os.domain.analysis import AnalysisKind
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


@dataclass(frozen=True)
class ExpectedOutcomeRequest:
    outcome_id: UUID
    metric: str
    operator: str
    target: float


@dataclass(frozen=True)
class ActualOutcomeRequest:
    outcome_id: UUID
    expected_outcome_id: UUID
    observed_value: float


@dataclass(frozen=True)
class EvidenceRequest:
    evidence_id: UUID
    source: str
    metric: str
    value: str
    unit: str
    period: str
    captured_at: str
    confidence: float
    snapshot: str


@dataclass(frozen=True)
class AnalysisFindingRequest:
    finding_id: UUID
    kind: AnalysisKind
    statement: str
    confidence: float
    evidence_ids: tuple[UUID, ...]


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
    create_expected_outcome_boundary: CreateExpectedOutcomeReliabilityBoundary | None = None,
    record_actual_outcome_boundary: RecordActualOutcomeReliabilityBoundary | None = None,
    verify_outcome_boundary: VerifyOutcomeReliabilityBoundary | None = None,
    create_evidence_boundary: CreateEvidenceReliabilityBoundary | None = None,
    add_analysis_finding_boundary: AddAnalysisFindingReliabilityBoundary | None = None,
    principal_provider: PrincipalProvider = get_principal,
    decision_memory_reader: DecisionMemoryReader | None = None,
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


    if create_evidence_boundary is not None:
        @router.post("/decision-cases/{case_id}/evidence", status_code=201)
        def create_evidence(case_id: UUID, body: EvidenceRequest, request: Request, principal: AuthenticatedPrincipal = Depends(principal_provider), idempotency_key: str = Header(..., alias="Idempotency-Key")) -> dict[str, object]:
            from datetime import datetime
            evidence = create_evidence_boundary.execute(CreateEvidenceCommand(
                tenant_id=principal.tenant_id, actor_id=principal.actor_id, case_id=case_id,
                evidence_id=body.evidence_id, source=body.source, metric=body.metric, value=body.value,
                unit=body.unit, period=body.period, captured_at=datetime.fromisoformat(body.captured_at),
                confidence=body.confidence, snapshot=body.snapshot,
            ), idempotency_key=idempotency_key, correlation_id=request.state.correlation_id)
            return {"data": {"id": str(evidence.id), "case_id": str(evidence.case_id), "source": evidence.source, "metric": evidence.metric, "value": evidence.value, "unit": evidence.unit, "period": evidence.period, "confidence": evidence.confidence}, "correlation_id": str(request.state.correlation_id)}

    if add_analysis_finding_boundary is not None:
        @router.post("/decision-cases/{case_id}/analysis/findings", status_code=201)
        def add_analysis_finding(case_id: UUID, body: AnalysisFindingRequest, request: Request, principal: AuthenticatedPrincipal = Depends(principal_provider), idempotency_key: str = Header(..., alias="Idempotency-Key")) -> dict[str, object]:
            finding = add_analysis_finding_boundary.execute(AddAnalysisFindingCommand(
                tenant_id=principal.tenant_id, actor_id=principal.actor_id, case_id=case_id,
                finding_id=body.finding_id, kind=body.kind, statement=body.statement,
                confidence=body.confidence, evidence_ids=body.evidence_ids,
            ), idempotency_key=idempotency_key, correlation_id=request.state.correlation_id)
            return {"data": {"id": str(finding.id), "case_id": str(finding.case_id), "kind": finding.kind.value, "statement": finding.statement, "confidence": finding.confidence, "evidence_ids": [str(value) for value in finding.evidence_ids]}, "correlation_id": str(request.state.correlation_id)}

    if create_expected_outcome_boundary is not None:
        @router.post("/decision-cases/{case_id}/outcomes/expected", status_code=201)
        def create_expected_outcome(case_id: UUID, body: ExpectedOutcomeRequest, request: Request, principal: AuthenticatedPrincipal = Depends(principal_provider), idempotency_key: str = Header(..., alias="Idempotency-Key")) -> dict[str, object]:
            outcome = create_expected_outcome_boundary.execute(CreateExpectedOutcomeCommand(tenant_id=principal.tenant_id, actor_id=principal.actor_id, case_id=case_id, outcome_id=body.outcome_id, metric=body.metric, operator=body.operator, target=body.target), idempotency_key=idempotency_key, correlation_id=request.state.correlation_id)
            return {"data": {"id": str(outcome.id), "case_id": str(outcome.case_id), "metric": outcome.metric, "operator": outcome.operator, "target": outcome.target}, "correlation_id": str(request.state.correlation_id)}

    if record_actual_outcome_boundary is not None:
        @router.post("/decision-cases/{case_id}/outcomes/actual", status_code=201)
        def record_actual_outcome(case_id: UUID, body: ActualOutcomeRequest, request: Request, principal: AuthenticatedPrincipal = Depends(principal_provider), idempotency_key: str = Header(..., alias="Idempotency-Key")) -> dict[str, object]:
            outcome = record_actual_outcome_boundary.execute(RecordActualOutcomeCommand(tenant_id=principal.tenant_id, actor_id=principal.actor_id, case_id=case_id, outcome_id=body.outcome_id, expected_outcome_id=body.expected_outcome_id, observed_value=body.observed_value), idempotency_key=idempotency_key, correlation_id=request.state.correlation_id)
            return {"data": {"id": str(outcome.id), "case_id": str(outcome.case_id), "expected_outcome_id": str(outcome.expected_outcome_id), "observed_value": outcome.observed_value, "status": outcome.status.value}, "correlation_id": str(request.state.correlation_id)}

    if verify_outcome_boundary is not None:
        @router.post("/decision-cases/{case_id}/outcomes/{actual_outcome_id}/verify", status_code=200)
        def verify_outcome(case_id: UUID, actual_outcome_id: UUID, request: Request, principal: AuthenticatedPrincipal = Depends(principal_provider), idempotency_key: str = Header(..., alias="Idempotency-Key"), verification_id: UUID = Header(..., alias="X-Verification-ID")) -> dict[str, object]:
            verification = verify_outcome_boundary.execute(VerifyOutcomeCommand(tenant_id=principal.tenant_id, actor_id=principal.actor_id, case_id=case_id, verification_id=verification_id, actual_outcome_id=actual_outcome_id), idempotency_key=idempotency_key, correlation_id=request.state.correlation_id)
            return {"data": {"id": str(verification.id), "case_id": str(verification.case_id), "actual_outcome_id": str(verification.actual_outcome_id), "status": verification.status.value}, "correlation_id": str(request.state.correlation_id)}
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

    if decision_memory_reader is not None:
        @router.get("/decision-cases/{case_id}/history", status_code=200)
        def get_decision_history(
            case_id: UUID,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
        ) -> dict[str, object]:
            view = decision_memory_reader.get(tenant_id=principal.tenant_id, case_id=case_id)
            if view is None:
                raise HTTPException(status_code=404, detail="decision history not found")
            return {
                "data": {
                    "case": {
                        "id": str(view.case_id),
                        "type": view.case_type,
                        "title": view.case_title,
                        "status": view.case_status,
                    },
                    "decision": {
                        "id": str(view.decision_id) if view.decision_id else None,
                        "status": view.decision_status,
                        "rationale": view.rationale,
                        "decided_by": str(view.decided_by) if view.decided_by else None,
                        "selected_option_ids": [str(value) for value in view.selected_option_ids],
                        "approval_required": view.approval_required,
                    },
                    "action": view.action_summary,
                    "outcome": view.outcome_summary,
                    "verification": view.verification_summary,
                    "source_ids": view.source_ids,
                    "projection": {
                        "state": view.state,
                        "authoritative_version": view.authoritative_version,
                        "notified_version": view.notified_version,
                        "projected_version": view.projected_version,
                        "projected_at": view.projected_at.isoformat(),
                    },
                },
                "correlation_id": str(request.state.correlation_id),
            }

    if decision_memory_reader is not None:
        @router.get("/decision-cases/{case_id}/memory", status_code=200)
        def get_decision_memory(
            case_id: UUID,
            request: Request,
            principal: AuthenticatedPrincipal = Depends(principal_provider),
        ) -> dict[str, object]:
            view = decision_memory_reader.get(tenant_id=principal.tenant_id, case_id=case_id)
            if view is None:
                raise HTTPException(status_code=404, detail="decision memory not found")
            return {
                "data": {
                    "case_id": str(view.case_id),
                    "tenant_id": str(view.tenant_id),
                    "case_type": view.case_type,
                    "case_title": view.case_title,
                    "case_status": view.case_status,
                    "decision": {
                        "id": str(view.decision_id) if view.decision_id else None,
                        "status": view.decision_status,
                        "rationale": view.rationale,
                        "decided_by": str(view.decided_by) if view.decided_by else None,
                        "selected_option_ids": [str(value) for value in view.selected_option_ids],
                        "approval_required": view.approval_required,
                    },
                    "action": view.action_summary,
                    "outcome": view.outcome_summary,
                    "verification": view.verification_summary,
                    "source_ids": view.source_ids,
                    "projection": {
                        "state": view.state,
                        "authoritative_version": view.authoritative_version,
                        "notified_version": view.notified_version,
                        "projected_version": view.projected_version,
                        "projected_at": view.projected_at.isoformat(),
                    },
                },
                "correlation_id": str(request.state.correlation_id),
            }

    return router
