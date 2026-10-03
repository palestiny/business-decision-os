from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from decision_os.domain.outcome import ActualOutcome, ExpectedOutcome, OutcomeStatus, Verification, VerificationStatus
from decision_os.infrastructure.persistence.models.outcome import ActualOutcomeModel, ExpectedOutcomeModel, VerificationModel


class SQLAlchemyExpectedOutcomeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, outcome_id: UUID, tenant_id: UUID) -> ExpectedOutcome | None:
        row = self._session.execute(select(ExpectedOutcomeModel).where(ExpectedOutcomeModel.id == outcome_id, ExpectedOutcomeModel.tenant_id == tenant_id)).scalar_one_or_none()
        return None if row is None else ExpectedOutcome(id=row.id, case_id=row.case_id, metric=row.metric, operator=row.operator, target=float(Decimal(row.target)))

    def add(self, outcome: ExpectedOutcome, tenant_id: UUID) -> None:
        self._session.add(ExpectedOutcomeModel(id=outcome.id, tenant_id=tenant_id, case_id=outcome.case_id, metric=outcome.metric, operator=outcome.operator, target=str(outcome.target)))


class SQLAlchemyActualOutcomeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, outcome_id: UUID, tenant_id: UUID) -> ActualOutcome | None:
        row = self._session.execute(select(ActualOutcomeModel).where(ActualOutcomeModel.id == outcome_id, ActualOutcomeModel.tenant_id == tenant_id)).scalar_one_or_none()
        return None if row is None else ActualOutcome(id=row.id, case_id=row.case_id, expected_outcome_id=row.expected_outcome_id, observed_value=float(Decimal(row.observed_value)), status=OutcomeStatus(row.status))

    def add(self, outcome: ActualOutcome, tenant_id: UUID) -> None:
        self._session.add(ActualOutcomeModel(id=outcome.id, tenant_id=tenant_id, case_id=outcome.case_id, expected_outcome_id=outcome.expected_outcome_id, observed_value=str(outcome.observed_value), status=outcome.status.value))

    def save(self, outcome: ActualOutcome, tenant_id: UUID) -> None:
        self._session.execute(update(ActualOutcomeModel).where(ActualOutcomeModel.id == outcome.id, ActualOutcomeModel.tenant_id == tenant_id).values(status=outcome.status.value))


class SQLAlchemyVerificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, verification_id: UUID, tenant_id: UUID) -> Verification | None:
        row = self._session.execute(select(VerificationModel).where(VerificationModel.id == verification_id, VerificationModel.tenant_id == tenant_id)).scalar_one_or_none()
        return None if row is None else Verification(id=row.id, case_id=row.case_id, actual_outcome_id=row.actual_outcome_id, status=VerificationStatus(row.status))

    def add(self, verification: Verification, tenant_id: UUID) -> None:
        self._session.add(VerificationModel(id=verification.id, tenant_id=tenant_id, case_id=verification.case_id, actual_outcome_id=verification.actual_outcome_id, status=verification.status.value))

    def save(self, verification: Verification, tenant_id: UUID) -> None:
        self._session.execute(update(VerificationModel).where(VerificationModel.id == verification.id, VerificationModel.tenant_id == tenant_id).values(status=verification.status.value))
