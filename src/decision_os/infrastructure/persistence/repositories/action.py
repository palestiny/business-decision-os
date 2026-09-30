from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from decision_os.domain.action import Action, ActionExecution, ActionExecutionStatus, ActionStatus, InvalidAction
from decision_os.infrastructure.persistence.models.action import ActionExecutionModel, ActionModel


class SQLAlchemyActionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, action_id: UUID, tenant_id: UUID) -> Action | None:
        row = self._session.execute(select(ActionModel).where(ActionModel.id == action_id, ActionModel.tenant_id == tenant_id)).scalar_one_or_none()
        if row is None:
            return None
        return Action(id=row.id, tenant_id=row.tenant_id, case_id=row.case_id, decision_id=row.decision_id, action_type=row.action_type, parameters=row.parameters, status=ActionStatus(row.status), version=row.version)

    def add(self, action: Action) -> None:
        self._session.add(ActionModel(id=action.id, tenant_id=action.tenant_id, case_id=action.case_id, decision_id=action.decision_id, action_type=action.action_type, parameters=action.parameters, status=action.status.value, version=action.version))

    def save(self, action: Action, *, expected_version: int) -> None:
        result = self._session.execute(update(ActionModel).where(ActionModel.id == action.id, ActionModel.tenant_id == action.tenant_id, ActionModel.version == expected_version).values(status=action.status.value, version=action.version))
        if result.rowcount != 1:
            raise InvalidAction("action version conflict")


class SQLAlchemyActionExecutionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: ActionExecutionModel) -> ActionExecution:
        return ActionExecution(id=row.id, action_id=row.action_id, attempt=row.attempt, status=ActionExecutionStatus(row.status))

    def get(self, execution_id: UUID) -> ActionExecution | None:
        row = self._session.execute(select(ActionExecutionModel).where(ActionExecutionModel.id == execution_id)).scalar_one_or_none()
        return None if row is None else self._to_domain(row)

    def get_latest_for_action(self, action_id: UUID) -> ActionExecution | None:
        row = self._session.execute(select(ActionExecutionModel).where(ActionExecutionModel.action_id == action_id).order_by(ActionExecutionModel.attempt.desc()).limit(1)).scalar_one_or_none()
        return None if row is None else self._to_domain(row)

    def save(self, execution: ActionExecution) -> None:
        result = self._session.execute(update(ActionExecutionModel).where(ActionExecutionModel.id == execution.id).values(status=execution.status.value))
        if result.rowcount != 1:
            raise InvalidAction("execution not found")

    def add(self, execution: ActionExecution) -> None:
        self._session.add(ActionExecutionModel(id=execution.id, action_id=execution.action_id, attempt=execution.attempt, status=execution.status.value))
