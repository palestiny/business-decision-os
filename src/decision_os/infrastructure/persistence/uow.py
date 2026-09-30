from sqlalchemy.orm import Session

from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.infrastructure.persistence.repositories.action import SQLAlchemyActionExecutionRepository, SQLAlchemyActionRepository
from decision_os.infrastructure.persistence.repositories.decision_case import SQLAlchemyDecisionCaseRepository
from decision_os.infrastructure.persistence.repositories.decision import SQLAlchemyDecisionRepository
from decision_os.infrastructure.persistence.repositories.decision_option import SQLAlchemyDecisionOptionRepository
from decision_os.infrastructure.persistence.repositories.outcome import SQLAlchemyActualOutcomeRepository, SQLAlchemyExpectedOutcomeRepository, SQLAlchemyVerificationRepository


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        self._session = session
        self.decision_cases = SQLAlchemyDecisionCaseRepository(session)
        self.decision_options = SQLAlchemyDecisionOptionRepository(session)
        self.decisions = SQLAlchemyDecisionRepository(session)
        self.actions = SQLAlchemyActionRepository(session)
        self.action_executions = SQLAlchemyActionExecutionRepository(session)
        self.expected_outcomes = SQLAlchemyExpectedOutcomeRepository(session)
        self.actual_outcomes = SQLAlchemyActualOutcomeRepository(session)
        self.verifications = SQLAlchemyVerificationRepository(session)

    def commit(self) -> None: self._session.commit()
    def rollback(self) -> None: self._session.rollback()
