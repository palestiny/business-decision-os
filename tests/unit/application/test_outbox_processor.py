from datetime import datetime, timezone
from uuid import uuid4

import pytest

from decision_os.application.outbox_processor import OutboxProcessor
from decision_os.application.ports.outbox import OutboxRecord


class Repo:
    def __init__(self, record): self.record = record; self.marked = []
    def get_unpublished(self, *, limit=100): return (self.record,)
    def mark_published(self, *, message_id, published_at): self.marked.append((message_id, published_at))


class Publication:
    def __init__(self): self.published=[]
    def publish(self, message): self.published.append(message)


class Tx:
    def __init__(self): self.commits=0; self.rollbacks=0
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


class Projector:
    def __init__(self, fail=False): self.calls=[]; self.fail=fail
    def project(self, *, tenant_id, case_id, notified_version=None):
        self.calls.append((tenant_id, case_id))
        if self.fail: raise RuntimeError("projection failed")


def record():
    return OutboxRecord(id=uuid4(), tenant_id=uuid4(), correlation_id=uuid4(), topic="decision-case.closed", aggregate_type="DecisionCase", aggregate_id=uuid4(), payload="{}", occurred_at=datetime.now(timezone.utc), published_at=None)


def test_decision_case_outbox_triggers_authoritative_projection_before_ack():
    r, p, tx, projector = Repo(record()), Publication(), Tx(), Projector()
    assert OutboxProcessor(repository=r, publication=p, transaction=tx, decision_memory=projector).process() == 1
    assert len(projector.calls) == 1
    assert len(r.marked) == 1
    assert tx.commits == 1


def test_projection_failure_rolls_back_and_does_not_mark_published():
    r, p, tx, projector = Repo(record()), Publication(), Tx(), Projector(fail=True)
    with pytest.raises(RuntimeError, match="projection failed"):
        OutboxProcessor(repository=r, publication=p, transaction=tx, decision_memory=projector).process()
    assert r.marked == []
    assert tx.commits == 0
    assert tx.rollbacks == 1
