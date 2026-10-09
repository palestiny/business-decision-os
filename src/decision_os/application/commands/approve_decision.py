from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission, SeparationOfDutiesViolation
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.decision import Decision


@dataclass(frozen=True)
class ApproveDecisionCommand:
    tenant_id: UUID
    case_id: UUID
    decision_id: UUID
    actor_id: UUID
    correlation_id: UUID | None = None

class ApproveDecisionHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: ApproveDecisionCommand) -> Decision:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise ValueError("decision case not found")

        self._authorization.require(
            actor_id=command.actor_id,
            tenant_id=command.tenant_id,
            permission=Permission.APPROVE_DECISION,
            resource_id=command.case_id,
            correlation_id=command.correlation_id)

        decision = self._uow.decisions.get(command.decision_id, command.tenant_id)
        if decision is None or decision.case_id != case.id:
            raise ValueError("decision not found")

        if case.created_by is None:
            raise SeparationOfDutiesViolation("cannot approve a case without recorded creator attribution")
        if command.actor_id == case.created_by:
            raise SeparationOfDutiesViolation("case creator cannot approve the decision")
        if command.actor_id == decision.decided_by:
            raise SeparationOfDutiesViolation("decision maker cannot approve their own decision")

        decision.approve(actor_id=command.actor_id, approved_at=datetime.now(timezone.utc))
        self._uow.decisions.save(decision, command.tenant_id)
        case.approve()
        self._uow.decision_cases.save(case)
        return decision
