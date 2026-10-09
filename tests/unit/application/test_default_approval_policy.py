from uuid import uuid4

from decision_os.application.approval_policy import RequireApprovalForEveryDecisionPolicy


def test_default_policy_requires_approval_and_returns_stable_policy_id():
    policy = RequireApprovalForEveryDecisionPolicy()

    first = policy.evaluate(actor_id=uuid4(), tenant_id=uuid4(), case_id=uuid4())
    second = policy.evaluate(actor_id=uuid4(), tenant_id=uuid4(), case_id=uuid4())

    assert first.required is True
    assert first.policy_ids == (RequireApprovalForEveryDecisionPolicy.POLICY_ID,)
    assert second.required is True
    assert second.policy_ids == first.policy_ids
