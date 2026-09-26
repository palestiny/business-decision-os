from uuid import uuid4

import pytest

from decision_os.application.commands.create_decision_case import (
    CreateDecisionCaseCommand,
    CreateDecisionCaseHandler,
)
from decision_os.application.ports.authority import Permission
from decision_os.application.ports.idempotency import IdempotencyConflict, IdempotencyRecord, RequestInProgress
from decision_os.application.reliability import CreateDecisionCaseReliabilityBoundary
from decision_os.domain.decision_case import DecisionCase


class Cases:
    def __init__(self):
        self.items = {}

    def add(self, case):
        self.items[(case.tenant_id, case.id)] = case

    def get(self, case_id, tenant_id):
        return self.items.get((tenant_id, case_id))


class Uow:
    def __init__(self):
        self.decision_cases = Cases()
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class Authorization:
    def require(self, **kwargs):
        assert kwargs["permission"] is Permission.CREATE_CASE


class Idempotency:
    def __init__(self):
        self.records = {}
        self.completed = 0

    def reserve(self, **kwargs):
        key = (kwargs["tenant_id"], kwargs["operation"], kwargs["key"])
        existing = self.records.get(key)
        if existing is None:
            record = IdempotencyRecord(**kwargs, status="IN_PROGRESS")
            self.records[key] = record
            return record
        if existing.request_hash != kwargs["request_hash"]:
            raise IdempotencyConflict
        if existing.status != "COMPLETED":
            raise RequestInProgress
        return existing

    def complete(self, **kwargs):
        key = (kwargs["tenant_id"], kwargs["operation"], kwargs["key"])
        old = self.records[key]
        self.records[key] = IdempotencyRecord(
            tenant_id=old.tenant_id,
            operation=old.operation,
            key=old.key,
            request_hash=old.request_hash,
            status="COMPLETED",
            response_status=kwargs["response_status"],
            response_body=kwargs["response_body"],
        )
        self.completed += 1


class Audit:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)


class Outbox:
    def __init__(self):
        self.messages = []

    def add(self, message):
        self.messages.append(message)


def build_boundary():
    uow = Uow()
    handler = CreateDecisionCaseHandler(uow, Authorization())
    return (
        CreateDecisionCaseReliabilityBoundary(
            uow=uow,
            handler=handler,
            idempotency=Idempotency(),
            audit=Audit(),
            outbox=Outbox(),
        ),
        uow,
    )


def test_create_case_reliability_boundary_commits_domain_and_reliability_together():
    boundary, uow = build_boundary()
    command = CreateDecisionCaseCommand(
        tenant_id=uuid4(),
        case_type="PROJECT_MARGIN_RISK",
        title="Margin risk",
        actor_id=uuid4(),
    )

    case = boundary.execute(command, idempotency_key="req-1")

    assert case.id is not None
    assert uow.commits == 1
    assert uow.rollbacks == 0
    assert len(boundary._audit.events) == 1
    assert len(boundary._outbox.messages) == 1
    assert boundary._idempotency.completed == 1


def test_create_case_duplicate_key_reuses_completed_response():
    boundary, uow = build_boundary()
    command = CreateDecisionCaseCommand(
        tenant_id=uuid4(),
        case_type="PROJECT_MARGIN_RISK",
        title="Margin risk",
        actor_id=uuid4(),
    )

    first = boundary.execute(command, idempotency_key="req-1")
    second = boundary.execute(command, idempotency_key="req-1")

    assert second.id == first.id
    assert uow.commits == 1


def test_create_case_rejects_same_key_for_different_request():
    boundary, _ = build_boundary()
    command = CreateDecisionCaseCommand(
        tenant_id=uuid4(),
        case_type="PROJECT_MARGIN_RISK",
        title="Margin risk",
        actor_id=uuid4(),
    )
    boundary.execute(command, idempotency_key="req-1")

    changed = CreateDecisionCaseCommand(
        tenant_id=command.tenant_id,
        case_type=command.case_type,
        title="Changed",
        actor_id=command.actor_id,
    )
    with pytest.raises(IdempotencyConflict):
        boundary.execute(changed, idempotency_key="req-1")
