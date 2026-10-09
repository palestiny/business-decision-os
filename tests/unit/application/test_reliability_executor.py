from uuid import uuid4

import pytest

from decision_os.application.ports.audit import AuditEvent
from decision_os.application.ports.idempotency import IdempotencyRecord
from decision_os.application.ports.outbox import OutboxMessage
from decision_os.application.reliability_executor import ReliabilityExecutor, ReliabilitySpec


class Uow:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class Idempotency:
    def __init__(self):
        self.records = {}

    def reserve(self, *, tenant_id, operation, key, request_hash):
        return self.records.setdefault(
            (tenant_id, operation, key),
            IdempotencyRecord(tenant_id, operation, key, request_hash, "IN_PROGRESS"),
        )

    def complete(self, *, tenant_id, operation, key, response_status, response_body):
        current = self.records[(tenant_id, operation, key)]
        self.records[(tenant_id, operation, key)] = IdempotencyRecord(
            current.tenant_id, current.operation, current.key, current.request_hash,
            "COMPLETED", response_status, response_body,
        )


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


def spec(execute):
    return ReliabilitySpec(
        operation="TestCommand",
        response_status=200,
        tenant_id=lambda c: c["tenant_id"],
        request_hash=lambda c: c["hash"],
        actor_id=lambda c: c["actor_id"],
        execute=execute,
        entity_id=lambda r: r["id"],
        entity_type="TestEntity",
        serialize=lambda r: r["value"],
        deserialize=lambda body: {"id": uuid4(), "value": body},
        outbox_topic="test.completed",
        outbox_payload=lambda r: '{"value": "' + r["value"] + '"}',
    )


def test_generic_executor_owns_atomic_success_path():
    uow = Uow()
    idem = Idempotency()
    audit = Audit()
    outbox = Outbox()
    executor = ReliabilityExecutor(uow=uow, idempotency=idem, audit=audit, outbox=outbox)
    entity_id = uuid4()
    command = {"tenant_id": uuid4(), "actor_id": uuid4(), "hash": "h1"}

    result = executor.execute(
        command,
        spec=spec(lambda _: {"id": entity_id, "value": "ok"}),
        idempotency_key="k1",
    )

    assert result["id"] == entity_id
    assert uow.commits == 1
    assert uow.rollbacks == 0
    assert len(audit.items) == 1
    assert len(outbox.items) == 1
    assert idem.records[(command["tenant_id"], "TestCommand", "k1")].status == "COMPLETED"


def test_generic_executor_replays_completed_request_without_side_effects():
    uow = Uow()
    idem = Idempotency()
    audit = Audit()
    outbox = Outbox()
    executor = ReliabilityExecutor(uow=uow, idempotency=idem, audit=audit, outbox=outbox)
    command = {"tenant_id": uuid4(), "actor_id": uuid4(), "hash": "h1"}
    calls = []

    s = spec(lambda _: calls.append(1) or {"id": uuid4(), "value": "ok"})
    first = executor.execute(command, spec=s, idempotency_key="k1")
    second = executor.execute(command, spec=s, idempotency_key="k1")

    assert second["value"] == first["value"]
    assert calls == [1]
    assert uow.commits == 1
    assert len(audit.items) == 1
    assert len(outbox.items) == 1


class FailingOutbox(Outbox):
    def add(self, message):
        raise RuntimeError("forced outbox failure")


def test_generic_executor_rolls_back_on_reliability_failure():
    uow = Uow()
    idem = Idempotency()
    audit = Audit()
    executor = ReliabilityExecutor(
        uow=uow, idempotency=idem, audit=audit, outbox=FailingOutbox()
    )
    command = {"tenant_id": uuid4(), "actor_id": uuid4(), "hash": "h1"}

    with pytest.raises(RuntimeError, match="forced outbox failure"):
        executor.execute(
            command,
            spec=spec(lambda _: {"id": uuid4(), "value": "ok"}),
            idempotency_key="k1",
        )

    assert uow.commits == 0
    assert uow.rollbacks == 1
