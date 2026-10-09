from dataclasses import dataclass
from uuid import UUID

from decision_os.application.ports.authority import AuthorizationPort, Permission
from decision_os.application.ports.unit_of_work import UnitOfWork
from decision_os.domain.decision import DecisionOption, InvalidDecision


@dataclass(frozen=True)
class SubmittedOptions:
    case_id: UUID
    options: tuple[DecisionOption, ...]
    status: str
    version: int


@dataclass(frozen=True)
class SubmitOptionsCommand:
    tenant_id: UUID
    case_id: UUID
    actor_id: UUID
    options: tuple[tuple[UUID, str], ...]
    correlation_id: UUID | None = None

class SubmitOptionsHandler:
    def __init__(self, uow: UnitOfWork, authorization: AuthorizationPort) -> None:
        self._uow = uow
        self._authorization = authorization

    def handle(self, command: SubmitOptionsCommand) -> SubmittedOptions:
        case = self._uow.decision_cases.get(command.case_id, command.tenant_id)
        if case is None:
            raise ValueError("decision case not found")
        self._authorization.require(
            actor_id=command.actor_id,
            tenant_id=command.tenant_id,
            permission=Permission.SUBMIT_OPTIONS,
            resource_id=command.case_id,
            correlation_id=command.correlation_id)
        if not command.options:
            raise InvalidDecision("at least one decision option is required")
        if len({option_id for option_id, _ in command.options}) != len(command.options):
            raise InvalidDecision("decision option ids must be unique")
        findings = self._uow.analysis_findings.list_for_case(case_id=case.id, tenant_id=case.tenant_id)
        if not findings:
            raise InvalidDecision("at least one analysis finding is required before options")
        existing = self._uow.decision_options.list_for_case(case_id=case.id, tenant_id=case.tenant_id)
        if existing:
            raise InvalidDecision("decision options already exist for case")
        options = tuple(
            DecisionOption.create(id=option_id, case_id=case.id, title=title)
            for option_id, title in command.options
        )
        for option in options:
            self._uow.decision_options.add(option)
        case.submit_options()
        self._uow.decision_cases.save(case)
        return SubmittedOptions(case_id=case.id, options=options, status=case.status.value, version=case.version)
