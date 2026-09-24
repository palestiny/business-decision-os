from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.decision import Decision


@dataclass(frozen=True)
class ApproveDecisionCommand:
    tenant_id: UUID
    case_id: UUID
    decision: Decision


class ApproveDecisionHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def handle(self, command: ApproveDecisionCommand) -> Decision:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise ValueError("decision case not found")
        command.decision.approve()
        self._uow.commit()
        return command.decision
