from datetime import datetime, timezone
from uuid import uuid4

from decision_os.application.outbox_publication import (
    OutboxPublicationService,
    PublicationOutcomeUnknown,
)
from decision_os.application.ports.outbox import OutboxRecord


class Repository:
    def __init__(self, messages):
        self.messages = list(messages)
        self.marked = []

    def get_unpublished(self, *, limit=100):
        return tuple(self.messages[:limit])

    def mark_published(self, *, message_id, published_at):
        self.marked.append((message_id, published_at))


class Publisher:
    def __init__(self):
        self.published = []

    def publish(self, message):
        self.published.append(message)


class UnknownPublisher(Publisher):
    def publish(self, message):
        raise PublicationOutcomeUnknown("external acknowledgement timed out")


def message():
    return OutboxRecord(
        id=uuid4(),
        topic="decision-case.created",
        aggregate_type="DecisionCase",
        aggregate_id=uuid4(),
        payload='{"case_id":"example"}',
        occurred_at=datetime.now(timezone.utc),
        published_at=None,
    )


def test_publication_marks_record_only_after_successful_external_publish():
    record = message()
    repository = Repository([record])
    publisher = Publisher()
    result = OutboxPublicationService(repository=repository, publisher=publisher).publish_one(record)

    assert result.published is True
    assert result.outcome_known is True
    assert publisher.published == [record]
    assert repository.marked[0][0] == record.id


def test_external_timeout_is_unknown_and_does_not_mark_published():
    record = message()
    repository = Repository([record])
    publisher = UnknownPublisher()
    result = OutboxPublicationService(repository=repository, publisher=publisher).publish_one(record)

    assert result.published is False
    assert result.outcome_known is False
    assert repository.marked == []


def test_already_published_record_is_not_published_again():
    record = message()
    published = OutboxRecord(
        id=record.id,
        topic=record.topic,
        aggregate_type=record.aggregate_type,
        aggregate_id=record.aggregate_id,
        payload=record.payload,
        occurred_at=record.occurred_at,
        published_at=datetime.now(timezone.utc),
    )
    repository = Repository([published])
    publisher = Publisher()
    result = OutboxPublicationService(repository=repository, publisher=publisher).publish_one(published)

    assert result.published is True
    assert result.outcome_known is True
    assert publisher.published == []
    assert repository.marked == []
