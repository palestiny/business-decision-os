from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import (
    AuthorizationPort,
    Permission,
    PolicyEvaluatorPort,
)
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


class MakeDecisionHandler:
    def __init__(
        self,
        uow: UnitOfWork,
        authorization: AuthorizationPort,
        policy_evaluator: PolicyEvaluatorPort,
    ) -> None:
        self._uow = uow
        self._authorization = authorization
        self._policy_evaluator = policy_evaluator

    def handle(
        self,
        command: MakeDecisionCommand,
        *,
        case_options: tuple[DecisionOption, ...],
    ) -> Decision:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise ValueError("decision case not found")

        self._authorization.require(
            actor_id=command.actor_id,
            tenant_id=command.tenant_id,
            permission=Permission.MAKE_DECISION,
            resource_id=command.case_id,
        )
        approval = self._policy_evaluator.evaluate(
            actor_id=command.actor_id,
            tenant_id=command.tenant_id,
            case_id=command.case_id,
        )

        decision = Decision.make(
            id=command.decision_id,
            case_id=case.id,
            available_options=case_options,
            selected_option_ids=command.option_ids,
            rationale=command.rationale,
            decided_by=command.actor_id,
            approval_required=approval.required,
            policy_ids=approval.policy_ids,
        )
        self._uow.decisions.add(decision)
        case.record_decision(approval_required=decision.approval_required)
        self._uow.decision_cases.save(case)
        return decision
