"""Deterministic first-release decision approval policy."""

from uuid import UUID

from decision_os.application.ports.authority import ApprovalDecision, PolicyEvaluatorPort


class RequireApprovalForEveryDecisionPolicy(PolicyEvaluatorPort):
    """Require independent approval for every decision in the first release.

    The identifier is a stable policy version marker persisted on each decision.
    Replace this evaluator through runtime injection only when an explicit,
    reviewed policy matrix or external policy service is available.
    """

    POLICY_ID = UUID("7f89d3e1-0f30-4f88-9c57-3bbf12c6a001")

    def evaluate(self, *, actor_id: UUID, tenant_id: UUID, case_id: UUID) -> ApprovalDecision:
        # Inputs are intentionally not used to infer a lower-risk exception.
        return ApprovalDecision(required=True, policy_ids=(self.POLICY_ID,))
