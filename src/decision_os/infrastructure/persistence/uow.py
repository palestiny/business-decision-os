from sqlalchemy.orm import Session

from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.infrastructure.persistence.repositories.decision_case import SQLAlchemyDecisionCaseRepository


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        self._session = session
        self.decision_cases = SQLAlchemyDecisionCaseRepository(session)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
