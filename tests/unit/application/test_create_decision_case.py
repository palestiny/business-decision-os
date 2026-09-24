from uuid import uuid4

from decision_os.application.commands.create_decision_case import (
    CreateDecisionCaseCommand,
    CreateDecisionCaseHandler,
)
from decision_os.domain.decision_case import CaseStatus


class InMemoryDecisionCases:
    def __init__(self) -> None:
        self.items = {}

    def get(self, case_id, tenant_id):
        return self.items.get((tenant_id, case_id))

    def add(self, case) -> None:
        self.items[(case.tenant_id, case.id)] = case

    def save(self, case) -> None:
        self.items[(case.tenant_id, case.id)] = case


class FakeUow:
    def __init__(self) -> None:
        self.decision_cases = InMemoryDecisionCases()
        self.committed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False


def test_create_case_persists_and_commits() -> None:
    uow = FakeUow()
    handler = CreateDecisionCaseHandler(uow)

    case = handler.handle(
        CreateDecisionCaseCommand(
            tenant_id=uuid4(),
            case_type="PROJECT_MARGIN_RISK",
            title="Margin risk detected",
        )
    )

    assert case.status is CaseStatus.DETECTED
    assert uow.committed is True
    assert uow.decision_cases.get(case.id, case.tenant_id) is case
