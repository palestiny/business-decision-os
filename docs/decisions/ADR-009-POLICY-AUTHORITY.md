# ADR-009: Policy Authority for Approval Requirements

## Status

Accepted

## Context

The decision command currently accepts `approval_required` from its caller. That makes approval policy an input rather than an enforced business rule: a caller could request `false` even when a tenant policy should require approval.

The architecture already separates two concerns:

- **Authorization** answers whether an actor may perform a command.
- **Policy evaluation** answers whether the decision requires approval and which policies caused that requirement.

These concerns must remain separate.

## Decision

1. `PolicyEvaluatorPort` is authoritative for whether a decision requires approval.
2. `MakeDecisionCommand` must not be the source of truth for `approval_required`.
3. The decision creation flow evaluates policy before creating the `Decision`.
4. The evaluated policy identifiers are captured as part of the decision authority snapshot so later policy changes do not rewrite history.
5. `AuthorizationPort` remains responsible for command permissions such as making, approving, and rejecting decisions.
6. Approval is still a first-class domain transition: `DecisionMade` and `DecisionApproved` remain distinct.
7. A missing/unavailable policy result is not silently treated as `approval_required=false`; the application must fail closed for protected approval policy evaluation.
8. The initial implementation may serialize the authority snapshot into the existing persistence boundary; moving it to structured JSON/JSONB is a separate persistence decision.

## Trade-offs

### Policy-derived approval

**Pros**
- Prevents callers from bypassing approval policy.
- Keeps business authority centralized.
- Makes policy provenance auditable.

**Cons**
- Every decision creation now depends on a policy evaluation boundary.
- Tests and composition require a policy adapter even for simple deployments.

### Caller-supplied approval flag

**Pros**
- Simpler command contract.
- Easy to prototype without policy infrastructure.

**Cons**
- Unsafe as a source of truth.
- Makes approval policy advisory instead of enforceable.
- Creates a hidden privilege-escalation path.

## Rejected Alternative

Keep `approval_required` as a trusted command field and rely on callers to supply the correct value. Rejected because application callers are not an adequate enforcement boundary for tenant policy.

## Verification Requirements

Before exposing a production API:

- policy-required decisions cannot be created as already approved by overriding the command;
- policy evaluation failure fails closed;
- policy identifiers are persisted with the decision authority snapshot;
- authorization remains independent from policy evaluation;
- approval/rejection commands require explicit actor authority.
