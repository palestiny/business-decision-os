"""Decision and option domain objects."""
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


class DecisionStatus(StrEnum):
    MADE = "MADE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DecisionError(ValueError):
    """Base decision-domain validation error."""


class InvalidDecision(DecisionError):
    """Raised when a decision violates a domain invariant."""


@dataclass(frozen=True)
class DecisionOption:
    id: UUID
    case_id: UUID
    title: str


@dataclass
class Decision:
    id: UUID
    case_id: UUID
    selected_option_ids: tuple[UUID, ...]
    rationale: str
    status: DecisionStatus = DecisionStatus.MADE
    decided_by: UUID | None = None
    _approval_required: bool = field(default=False, repr=False)
    policy_ids: tuple[UUID, ...] = ()

    @classmethod
    def make(
        cls,
        *,
        id: UUID,
        case_id: UUID,
        available_options: tuple[DecisionOption, ...],
        selected_option_ids: tuple[UUID, ...],
        rationale: str,
        decided_by: UUID,
        approval_required: bool,
        policy_ids: tuple[UUID, ...] = (),
    ) -> "Decision":
        if not selected_option_ids:
            raise InvalidDecision("at least one option must be selected")
        if not rationale.strip():
            raise InvalidDecision("decision rationale is required")

        if len(selected_option_ids) != len(set(selected_option_ids)):
            raise InvalidDecision("selected options must be unique")

        if any(option.case_id != case_id for option in available_options):
            raise InvalidDecision("available option does not belong to the case")

        available_ids = {option.id for option in available_options}
        if not set(selected_option_ids).issubset(available_ids):
            raise InvalidDecision("selected option does not belong to the case")

        return cls(
            id=id,
            case_id=case_id,
            selected_option_ids=selected_option_ids,
            rationale=rationale,
            status=(
                DecisionStatus.AWAITING_APPROVAL
                if approval_required
                else DecisionStatus.APPROVED
            ),
            decided_by=decided_by,
            _approval_required=approval_required,
            policy_ids=policy_ids,
        )

    @property
    def approval_required(self) -> bool:
        return self._approval_required

    def approve(self) -> None:
        if not self._approval_required:
            raise InvalidDecision("decision does not require approval")
        if self.status is not DecisionStatus.AWAITING_APPROVAL:
            raise InvalidDecision("only pending decisions can be approved")
        self.status = DecisionStatus.APPROVED

    def reject(self) -> None:
        if self.status is not DecisionStatus.AWAITING_APPROVAL:
            raise InvalidDecision("only pending decisions can be rejected")
        self.status = DecisionStatus.REJECTED
