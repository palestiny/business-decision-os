from uuid import uuid4

from decision_os.application.ports.decision_work_queue import (
    DecisionWorkQueueItem,
    DecisionWorkQueuePage,
    DecisionWorkQueueReader,
)


class StubDecisionWorkQueueReader:
    def __init__(self, items):
        self._items = items

    def list(self, *, tenant_id, limit=50, cursor=None, attention_state=None, case_type=None):
        items = tuple(item for item in self._items if item.tenant_id == tenant_id)
        if attention_state is not None:
            items = tuple(item for item in items if item.attention_state == attention_state)
        if case_type is not None:
            items = tuple(item for item in items if item.case_type == case_type)
        return DecisionWorkQueuePage(items=items[:limit], next_cursor=None)


def test_work_queue_reader_returns_tenant_scoped_items_deterministically():
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    item = DecisionWorkQueueItem(
        tenant_id=tenant_id,
        case_id=uuid4(),
        case_type="PROJECT_MARGIN_RISK",
        title="Margin risk",
        case_status="AWAITING_DECISION",
        attention_state="MAKE_DECISION",
        decision_id=uuid4(),
        decision_status="PENDING",
        approval_required=False,
        authoritative_version=3,
        projection_state="CURRENT",
    )
    foreign_item = DecisionWorkQueueItem(
        tenant_id=other_tenant_id,
        case_id=uuid4(),
        case_type="PROJECT_MARGIN_RISK",
        title="Foreign margin risk",
        case_status="AWAITING_DECISION",
        attention_state="MAKE_DECISION",
        decision_id=None,
        decision_status=None,
        approval_required=None,
        authoritative_version=1,
        projection_state=None,
    )
    reader: DecisionWorkQueueReader = StubDecisionWorkQueueReader((item, foreign_item))

    assert reader.list(tenant_id=tenant_id).items == (item,)


def test_work_queue_item_contains_human_routing_context():
    item = DecisionWorkQueueItem(
        tenant_id=uuid4(),
        case_id=uuid4(),
        case_type="PROJECT_MARGIN_RISK",
        title="Margin risk",
        case_status="AWAITING_DECISION",
        attention_state="MAKE_DECISION",
        decision_id=uuid4(),
        decision_status="PENDING",
        approval_required=False,
        authoritative_version=3,
        projection_state="CURRENT",
    )

    assert item.attention_state == "MAKE_DECISION"
    assert item.authoritative_version == 3
