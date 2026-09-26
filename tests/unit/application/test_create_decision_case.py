from uuid import uuid4

from decision_os.application.commands.create_decision_case import (
    CreateDecisionCaseCommand,
    CreateDecisionCaseHandler,
)
from decision_os.application.ports.authority import Permission
from decision_os.domain.decision_case import CaseStatus


class Authorization:
    def __init__(self) -> None:
        self.calls = []

    def require(self, **kwargs) -> None:
        self.calls.append(kwargs)


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
    authorization = Authorization()
    handler = CreateDecisionCaseHandler(uow, authorization)
    tenant_id = uuid4()
    actor_id = uuid4()

    case = handler.handle(
        CreateDecisionCaseCommand(
            tenant_id=tenant_id,
            actor_id=actor_id,
            case_type="PROJECT_MARGIN_RISK",
            title="Margin risk detected",
        )
    )

    assert case.status is CaseStatus.DETECTED
    assert uow.committed is True
    assert uow.decision_cases.get(case.id, case.tenant_id) is case

    assert authorization.calls == [{
        "actor_id": actor_id,
        "tenant_id": tenant_id,
        "permission": Permission.CREATE_CASE,
        "resource_id": case.id,
    }]
