from uuid import uuid4

import pytest

from decision_os.application.ports.decision_work_queue import (
    DecisionWorkQueueReader,
    DecisionWorkQueueItem,
)


def test_work_queue_contract_returns_deterministic_attention_items():
    tenant_id = uuid4()
    case_id = uuid4()

    reader = DecisionWorkQueueReader()

    with pytest.raises(NotImplementedError):
        reader.list(tenant_id=tenant_id)


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
