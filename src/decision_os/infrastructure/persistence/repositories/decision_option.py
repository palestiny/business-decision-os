from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from decision_os.domain.decision import DecisionOption
from decision_os.infrastructure.persistence.models.decision import DecisionOptionModel
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel


class SQLAlchemyDecisionOptionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, option: DecisionOption) -> None:
        self._session.add(DecisionOptionModel(id=option.id, case_id=option.case_id, title=option.title))

    def list_for_case(self, *, case_id: UUID, tenant_id: UUID) -> tuple[DecisionOption, ...]:
        rows = self._session.execute(
            select(DecisionOptionModel)
            .join(DecisionCaseModel, DecisionCaseModel.id == DecisionOptionModel.case_id)
            .where(
                DecisionOptionModel.case_id == case_id,
                DecisionCaseModel.tenant_id == tenant_id,
            )
            .order_by(DecisionOptionModel.id)
        ).scalars().all()
        return tuple(
            DecisionOption(id=row.id, case_id=row.case_id, title=row.title)
            for row in rows
        )
