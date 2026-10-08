from uuid import uuid4

from decision_os.infrastructure.persistence.readers.decision_work_queue import (
    SessionFactoryDecisionWorkQueueReader,
)


class FakeSession:
    def __init__(self):
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.exited = True

    def execute(self, statement):
        return FakeResult()


class FakeResult:
    def all(self):
        return []


def test_reader_opens_and_closes_a_fresh_session_for_each_query():
    sessions = []

    def session_factory():
        session = FakeSession()
        sessions.append(session)
        return session

    reader = SessionFactoryDecisionWorkQueueReader(session_factory)

    assert reader.list(tenant_id=uuid4()) == ()
    assert reader.list(tenant_id=uuid4()) == ()

    assert len(sessions) == 2
    assert sessions[0] is not sessions[1]
    assert all(session.entered and session.exited for session in sessions)
