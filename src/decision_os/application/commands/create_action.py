from dataclasses import dataclass
from uuid import UUID, uuid4

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.action import Action, InvalidAction
from decision_os.domain.decision import DecisionStatus
from decision_os.domain.decision_case import CaseStatus


@dataclass(frozen=True)
class CreateActionCommand:
    tenant_id: UUID
    case_id: UUID
    decision_id: UUID
    actor_id: UUID
    action_type: str
    parameters: str
    action_id: UUID | None = None
    correlation_id: UUID | None = None

class CreateActionHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: CreateActionCommand) -> Action:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise InvalidAction("decision case not found")
        self._authorization.require(
            actor_id=command.actor_id, tenant_id=command.tenant_id,
            permission=Permission.CREATE_ACTION, resource_id=command.case_id,
            correlation_id=command.correlation_id)
        if case.status is not CaseStatus.APPROVED:
            raise InvalidAction("decision case must be approved before action creation")
        decision = self._uow.decisions.get(command.decision_id, command.tenant_id)
        if decision is None or decision.case_id != case.id:
            raise InvalidAction("decision not found")
        if decision.status is not DecisionStatus.APPROVED:
            raise InvalidAction("decision must be approved before action creation")
        action = Action.create(
            id=command.action_id or uuid4(), tenant_id=command.tenant_id,
            case_id=case.id, decision_id=decision.id,
            action_type=command.action_type, parameters=command.parameters,
        )
        action.ready()
        self._uow.actions.add(action)
        return action
