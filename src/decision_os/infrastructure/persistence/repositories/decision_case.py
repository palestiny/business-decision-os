from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from decision_os.domain.decision_case import CaseStatus, DecisionCase
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel


class SQLAlchemyDecisionCaseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, case_id: UUID, tenant_id: UUID) -> DecisionCase | None:
        model = self._session.scalar(
            select(DecisionCaseModel).where(
                DecisionCaseModel.id == case_id,
                DecisionCaseModel.tenant_id == tenant_id,
            )
        )
        if model is None:
            return None
        return DecisionCase(
            id=model.id,
            tenant_id=model.tenant_id,
            case_type=model.case_type,
            title=model.title,
            status=CaseStatus(model.status),
            version=model.version,
        )

    def add(self, case: DecisionCase) -> None:
        now = datetime.now(timezone.utc)
        self._session.add(DecisionCaseModel(
            id=case.id,
            tenant_id=case.tenant_id,
            case_type=case.case_type,
            title=case.title,
            status=case.status.value,
            version=case.version,
            created_at=now,
            updated_at=now,
        ))

    def save(self, case: DecisionCase) -> None:
        expected_previous_version = case.version - 1
        result = self._session.execute(
            update(DecisionCaseModel)
            .where(
                DecisionCaseModel.id == case.id,
                DecisionCaseModel.tenant_id == case.tenant_id,
                DecisionCaseModel.version == expected_previous_version,
            )
            .values(
                status=case.status.value,
                version=case.version,
                updated_at=datetime.now(timezone.utc),
            )
        )
        if result.rowcount != 1:
            raise RuntimeError("decision case concurrency conflict")
