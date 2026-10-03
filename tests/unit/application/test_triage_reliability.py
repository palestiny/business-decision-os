from uuid import uuid4

import pytest

from decision_os.application.commands.triage_case import TriageCaseCommand, TriageCaseHandler
from decision_os.application.ports.audit import AuditEvent
from decision_os.application.ports.idempotency import IdempotencyRecord
from decision_os.application.ports.outbox import OutboxMessage
from decision_os.application.triage_reliability import TriageCaseReliabilityBoundary
from decision_os.domain.decision_case import CaseStatus, DecisionCase


class Cases:
    def __init__(self, case):
        self.items = {(case.tenant_id, case.id): case}

    def get(self, case_id, tenant_id):
        return self.items.get((tenant_id, case_id))

    def save(self, case):
        self.items[(case.tenant_id, case.id)] = case


class Authorization:
    def require(self, **kwargs):
        pass


class Uow:
    def __init__(self, case):
        self.decision_cases = Cases(case)
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class Idempotency:
    def __init__(self):
        self.records = {}
        self.completed = []

    def reserve(self, *, tenant_id, operation, key, request_hash):
        existing = self.records.get((tenant_id, operation, key))
        if existing is not None:
            return existing
        record = IdempotencyRecord(
            tenant_id=tenant_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
            status="IN_PROGRESS",
        )
        self.records[(tenant_id, operation, key)] = record
        return record

    def complete(self, *, tenant_id, operation, key, response_status, response_body):
        current = self.records[(tenant_id, operation, key)]
        updated = IdempotencyRecord(
            tenant_id=current.tenant_id,
            operation=current.operation,
            key=current.key,
            request_hash=current.request_hash,
            status="COMPLETED",
            response_status=response_status,
            response_body=response_body,
        )
        self.records[(tenant_id, operation, key)] = updated
        self.completed.append(updated)


class Audit:
    def __init__(self):
        self.items = []

    def append(self, event: AuditEvent):
        self.items.append(event)


class Outbox:
    def __init__(self):
        self.items = []

    def add(self, message: OutboxMessage):
        self.items.append(message)


class FailingOutbox(Outbox):
    def add(self, message):
        raise RuntimeError("forced outbox failure")


def make_case():
    return DecisionCase.create(
        id=uuid4(),
        tenant_id=uuid4(),
        case_type="PROJECT_MARGIN_RISK",
        title="Margin risk",
    )


def make_boundary(case, *, outbox=None):
    uow = Uow(case)
    idempotency = Idempotency()
    audit = Audit()
    boundary = TriageCaseReliabilityBoundary(
        uow=uow,
        handler=TriageCaseHandler(uow, Authorization()),
        idempotency=idempotency,
        audit=audit,
        outbox=outbox or Outbox(),
    )
    return boundary, uow, idempotency, audit


def test_triage_reliability_boundary_commits_domain_and_reliability_together():
    case = make_case()
    boundary, uow, idempotency, audit = make_boundary(case)

    result = boundary.execute(
        TriageCaseCommand(case.tenant_id, case.id, uuid4()),
        idempotency_key="triage-success",
    )

    assert result.status is CaseStatus.TRIAGED
    assert result.version == 1
    assert uow.commits == 1
    assert uow.rollbacks == 0
    assert len(audit.items) == 1
    assert idempotency.records[(case.tenant_id, "TriageCase", "triage-success")].status == "COMPLETED"


def test_triage_reliability_boundary_replays_completed_response():
    case = make_case()
    boundary, uow, idempotency, audit = make_boundary(case)
    command = TriageCaseCommand(case.tenant_id, case.id, uuid4())

    first = boundary.execute(command, idempotency_key="triage-replay")
    second = boundary.execute(command, idempotency_key="triage-replay")

    assert second.id == first.id
    assert second.status is CaseStatus.TRIAGED
    assert uow.commits == 1
    assert len(audit.items) == 1


def test_triage_reliability_boundary_rolls_back_when_outbox_write_fails():
    case = make_case()
    failing_outbox = FailingOutbox()
    boundary, uow, idempotency, audit = make_boundary(case, outbox=failing_outbox)

    with pytest.raises(RuntimeError, match="forced outbox failure"):
        boundary.execute(
            TriageCaseCommand(case.tenant_id, case.id, uuid4()),
            idempotency_key="triage-failure",
        )

    assert uow.commits == 0
    assert uow.rollbacks == 1
    assert idempotency.records[(case.tenant_id, "TriageCase", "triage-failure")].status == "IN_PROGRESS"
    assert len(audit.items) == 1
