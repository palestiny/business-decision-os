from types import SimpleNamespace
from uuid import uuid4

from decision_os.domain.action import ActionStatus
from decision_os.domain.decision_case import CaseStatus
from decision_os.infrastructure.persistence.readers.decision_work_queue import SQLAlchemyDecisionWorkQueueReader


def test_attention_mapping_covers_human_workflow_states():
    reader = SQLAlchemyDecisionWorkQueueReader.__new__(SQLAlchemyDecisionWorkQueueReader)

    assert reader._attention(CaseStatus.AWAITING_DECISION.value, None) == "MAKE_DECISION"
    assert reader._attention(CaseStatus.AWAITING_APPROVAL.value, None) == "APPROVE_DECISION"
    assert reader._attention(CaseStatus.APPROVED.value, None, None) == "NO_ACTION"
    ready_action = SimpleNamespace(status=ActionStatus.READY.value)
    assert reader._attention(CaseStatus.APPROVED.value, None, ready_action) == "EXECUTE_ACTION"
    assert reader._attention(CaseStatus.VERIFYING.value, None) == "REVIEW_OUTCOME"
    assert reader._attention(CaseStatus.CLOSED.value, None) == "NO_ACTION"


def test_queue_priority_is_deterministic():
    reader = SQLAlchemyDecisionWorkQueueReader.__new__(SQLAlchemyDecisionWorkQueueReader)

    items = [
        ("REVIEW_OUTCOME", uuid4()),
        ("MAKE_DECISION", uuid4()),
        ("APPROVE_DECISION", uuid4()),
    ]

    ordered = sorted(items, key=lambda item: (reader._priority(item[0]), str(item[1])))

    assert [item[0] for item in ordered] == [
        "MAKE_DECISION",
        "APPROVE_DECISION",
        "REVIEW_OUTCOME",
    ]
