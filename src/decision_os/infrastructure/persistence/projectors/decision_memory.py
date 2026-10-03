from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from decision_os.application.ports.decision_memory import DecisionMemorySnapshot
from decision_os.infrastructure.persistence.models.action import ActionExecutionModel, ActionModel
from decision_os.infrastructure.persistence.models.decision import DecisionModel, DecisionSelectedOptionModel
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel
from decision_os.infrastructure.persistence.models.evidence import AnalysisFindingModel, EvidenceModel
from decision_os.infrastructure.persistence.models.outcome import ActualOutcomeModel, ExpectedOutcomeModel, VerificationModel
from decision_os.infrastructure.persistence.models.decision_memory import DecisionMemoryProjectionModel


class SQLAlchemyDecisionMemoryProjector:
    """Rebuilds the read model from current authoritative Decision Core tables."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def project(self, *, tenant_id: UUID, case_id: UUID, notified_version: int | None = None) -> DecisionMemorySnapshot:
        case = self._session.scalar(select(DecisionCaseModel).where(
            DecisionCaseModel.id == case_id,
            DecisionCaseModel.tenant_id == tenant_id,
        ))
        if case is None:
            raise ValueError("decision case not found")

        decision = self._session.scalar(select(DecisionModel).where(DecisionModel.case_id == case_id))
        option_ids = []
        if decision is not None:
            option_ids = [str(value) for value in self._session.scalars(select(DecisionSelectedOptionModel.option_id).where(DecisionSelectedOptionModel.decision_id == decision.id)).all()]

        action = self._session.scalar(select(ActionModel).where(ActionModel.case_id == case_id, ActionModel.tenant_id == tenant_id))
        execution = None
        if action is not None:
            execution = self._session.scalar(select(ActionExecutionModel).where(ActionExecutionModel.action_id == action.id).order_by(ActionExecutionModel.attempt.desc()))

        expected = self._session.scalar(select(ExpectedOutcomeModel).where(ExpectedOutcomeModel.case_id == case_id, ExpectedOutcomeModel.tenant_id == tenant_id))
        actual = self._session.scalar(select(ActualOutcomeModel).where(ActualOutcomeModel.case_id == case_id, ActualOutcomeModel.tenant_id == tenant_id))
        verification = self._session.scalar(select(VerificationModel).where(VerificationModel.case_id == case_id, VerificationModel.tenant_id == tenant_id))

        evidence_ids = [str(value) for value in self._session.scalars(select(EvidenceModel.id).where(EvidenceModel.case_id == case_id, EvidenceModel.tenant_id == tenant_id)).all()]
        finding_ids = [str(value) for value in self._session.scalars(select(AnalysisFindingModel.id).where(AnalysisFindingModel.case_id == case_id, AnalysisFindingModel.tenant_id == tenant_id)).all()]
        source_ids = {
            "evidence_ids": evidence_ids,
            "analysis_finding_ids": finding_ids,
            "decision_id": str(decision.id) if decision else None,
            "action_id": str(action.id) if action else None,
            "execution_id": str(execution.id) if execution else None,
            "expected_outcome_id": str(expected.id) if expected else None,
            "actual_outcome_id": str(actual.id) if actual else None,
            "verification_id": str(verification.id) if verification else None,
        }
        projected_at = datetime.now(timezone.utc)
        projection = self._session.scalar(select(DecisionMemoryProjectionModel).where(
            DecisionMemoryProjectionModel.tenant_id == tenant_id,
            DecisionMemoryProjectionModel.case_id == case_id,
        ))
        if projection is None:
            projection = DecisionMemoryProjectionModel(id=uuid4(), tenant_id=tenant_id, case_id=case_id)
            self._session.add(projection)

        previous_notified = projection.notified_version if projection is not None else None
        effective_notified = max(
            value for value in (previous_notified, notified_version, case.version)
            if value is not None
        )
        state = "STALE" if effective_notified > case.version else "CURRENT"

        projection.case_type = case.case_type
        projection.case_title = case.title
        projection.case_status = case.status
        projection.decision_id = decision.id if decision else None
        projection.decision_status = decision.status if decision else None
        projection.rationale = decision.rationale if decision else None
        projection.decided_by = decision.decided_by if decision else None
        projection.selected_option_ids = option_ids
        projection.approval_required = decision.approval_required if decision else None
        projection.action_summary = ({"id": str(action.id), "type": action.action_type, "status": action.status, "parameters": action.parameters, "execution_status": execution.status if execution else None} if action else None)
        projection.outcome_summary = ({"expected": {"id": str(expected.id), "metric": expected.metric, "operator": expected.operator, "target": expected.target} if expected else None, "actual": {"id": str(actual.id), "observed_value": actual.observed_value, "status": actual.status} if actual else None}) if (expected or actual) else None
        projection.verification_summary = ({"id": str(verification.id), "actual_outcome_id": str(verification.actual_outcome_id), "status": verification.status} if verification else None)
        projection.source_ids = source_ids
        projection.authoritative_version = case.version
        projection.notified_version = effective_notified
        projection.projected_version = case.version
        projection.projected_at = projected_at
        projection.last_projection_state = state
        self._session.flush()
        return DecisionMemorySnapshot(tenant_id=tenant_id, case_id=case_id, authoritative_version=case.version, projected_at=projected_at, state=state)

    def rebuild(self, *, tenant_id: UUID, case_id: UUID) -> DecisionMemorySnapshot:
        return self.project(tenant_id=tenant_id, case_id=case_id)
