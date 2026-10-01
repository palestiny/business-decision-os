import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, close_all_sessions

from decision_os.application.outbox_publication import OutboxPublicationService, PublicationOutcomeUnknown
from decision_os.application.ports.outbox import OutboxMessage
from decision_os.infrastructure.persistence.models.reliability import OutboxMessageModel
from decision_os.infrastructure.persistence.session import build_session_factory
from decision_os.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from decision_os.infrastructure.persistence.repositories.reliability import SQLAlchemyOutboxRepository

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests")

@pytest.fixture()
def session():
    factory = build_session_factory(DATABASE_URL)
    with factory() as db:
        yield db
        db.rollback()
    close_all_sessions()

class RecordingPublisher:
    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)

class UnknownPublisher:
    def publish(self, message):
        raise PublicationOutcomeUnknown("external acknowledgement timed out")

def seed_outbox(session: Session):
    message = OutboxMessage(
        id=uuid4(),
        tenant_id=uuid4(),
        correlation_id=uuid4(),
        topic="decision-case.created",
        aggregate_type="DecisionCase",
        aggregate_id=uuid4(),
        payload='{"case_id":"example"}',
        occurred_at=datetime.now(timezone.utc),
    )
    SQLAlchemyOutboxRepository(session).add(message)
    session.commit()
    return message

def test_postgres_outbox_publication_marks_message_only_after_external_success(session: Session):
    message = seed_outbox(session)
    repository = SQLAlchemyOutboxRepository(session)
    publisher = RecordingPublisher()
    transaction = SQLAlchemyUnitOfWork(session)
    service = OutboxPublicationService(repository=repository, publisher=publisher, transaction=transaction)
    result = service.publish_one(next(item for item in repository.get_unpublished() if item.id == message.id))
    assert result.message_id == message.id
    assert result.published is True
    assert result.outcome_known is True
    assert [item.id for item in publisher.messages] == [message.id]
    persisted = session.scalar(select(OutboxMessageModel).where(OutboxMessageModel.id == message.id))
    assert persisted is not None
    assert persisted.published_at is not None
    assert persisted.tenant_id == message.tenant_id
    assert persisted.correlation_id == message.correlation_id

def test_postgres_outbox_publication_leaves_message_unpublished_when_delivery_outcome_is_unknown(session: Session):
    message = seed_outbox(session)
    repository = SQLAlchemyOutboxRepository(session)
    transaction = SQLAlchemyUnitOfWork(session)
    service = OutboxPublicationService(repository=repository, publisher=UnknownPublisher(), transaction=transaction)
    result = service.publish_one(next(item for item in repository.get_unpublished() if item.id == message.id))
    assert result.message_id == message.id
    assert result.published is False
    assert result.outcome_known is False
    persisted = session.scalar(select(OutboxMessageModel).where(OutboxMessageModel.id == message.id))
    assert persisted is not None
    assert persisted.published_at is None
