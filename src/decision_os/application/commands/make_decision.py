from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.decision import Decision, DecisionOption


@dataclass(frozen=True)
class MakeDecisionCommand:
    tenant_id: UUID
    case_id: UUID
    decision_id: UUID
    option_ids: tuple[UUID, ...]
    rationale: str
    actor_id: UUID
    approval_required: bool


class MakeDecisionHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def handle(
        self,
        command: MakeDecisionCommand,
        *,
        case_options: tuple[DecisionOption, ...],
    ) -> Decision:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise ValueError("decision case not found")

        decision = Decision.make(
            id=command.decision_id,
            case_id=case.id,
            available_options=case_options,
            selected_option_ids=command.option_ids,
            rationale=command.rationale,
            decided_by=command.actor_id,
            approval_required=command.approval_required,
        )
        self._uow.decisions.add(decision)
        case.record_decision(approval_required=decision.approval_required)
        self._uow.decision_cases.save(case)
        self._uow.commit()
        return decision
