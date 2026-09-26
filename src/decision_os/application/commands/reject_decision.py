from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.decision import Decision


@dataclass(frozen=True)
class RejectDecisionCommand:
    tenant_id: UUID
    case_id: UUID
    decision_id: UUID
    actor_id: UUID


class RejectDecisionHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: RejectDecisionCommand) -> Decision:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise ValueError("decision case not found")

        self._authorization.require(
            actor_id=command.actor_id,
            tenant_id=command.tenant_id,
            permission=Permission.REJECT_DECISION,
            resource_id=command.case_id,
        )

        decision = self._uow.decisions.get(command.decision_id, command.tenant_id)
        if decision is None or decision.case_id != case.id:
            raise ValueError("decision not found")

        decision.reject()
        self._uow.decisions.save(decision, command.tenant_id)
        case.reject()
        self._uow.decision_cases.save(case)
        self._uow.commit()
        return decision
