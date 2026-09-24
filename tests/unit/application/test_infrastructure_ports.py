from datetime import UTC, datetime
from uuid import uuid4

import pytest

from decision_os.application.ports.authority import (
    ApprovalDecision,
    AuthorizationDenied,
    Permission,
)
from decision_os.application.ports.idempotency import (
    IdempotencyConflict,
    RequestInProgress,
)
from decision_os.application.ports.outbox import OutboxMessage


def test_approval_policy_is_explicit() -> None:
    result = ApprovalDecision(required=True, policy_ids=(uuid4(),))
    assert result.required is True
    assert len(result.policy_ids) == 1


def test_permission_denial_is_distinct_from_domain_validation() -> None:
    with pytest.raises(AuthorizationDenied):
        raise AuthorizationDenied("approve permission denied")


def test_idempotency_failures_are_distinct() -> None:
    assert IdempotencyConflict.__name__ != RequestInProgress.__name__


def test_outbox_message_has_stable_identity_and_timestamp() -> None:
    message = OutboxMessage(
        id=uuid4(),
        topic="decision.made",
        aggregate_type="DecisionCase",
        aggregate_id=uuid4(),
        payload="{}",
        occurred_at=datetime.now(UTC),
    )
    assert message.id
    assert message.occurred_at.tzinfo is UTC
    assert message.topic == "decision.made"
