# CHECKPOINT-012

## Scope

Authority enforcement and policy authority at the decision approval boundary.

## Verified

- GitHub Actions run 62 for commit `6e4adacbe072d71356fc6bc1f08c38edf6236f19` completed successfully.
- PostgreSQL 17 integration path passed across Python 3.12 and 3.13.
- PostgreSQL decision persistence now verifies approval and rejection lifecycle state.
- Alembic migration round-trip and current-head verification passed.
- Alembic drift checking is part of CI.
- The earlier PostgreSQL FK ordering and SQLAlchemy session-cleanup failures are resolved.

SQLAlchemy's current 2.0 documentation continues to require explicit transaction framing: commit on success and rollback after a failed flush/transaction before reusing the Session. citeturn0search0turn0search2

## Added

- ApproveDecisionCommand carries the approving actor identity.
- ApproveDecisionHandler requires AuthorizationPort.
- Approval authorization is checked with Permission.APPROVE_DECISION before mutating the Decision.
- Unit coverage verifies the authority call contract and tenant/case scoping.
- ADR-009 establishes policy evaluation as the authoritative source of approval requirements.

## Architectural rule

Approval has two independent boundaries:

1. **Policy evaluation** determines whether a decision requires approval and which policies caused that requirement.
2. **Authorization** determines whether the current actor may approve or reject the decision.

A valid domain state alone is not sufficient to authorize approval.

## Decision

The caller must not be the source of truth for `approval_required`. The policy evaluator owns that decision, and the evaluated policy identifiers must be retained in an authority snapshot for historical traceability.

See `docs/decisions/ADR-009-POLICY-AUTHORITY.md`.

## Verification boundary

The policy evaluator is currently only an application port; no production policy adapter is wired yet.

The following command boundaries still need consistent authority enforcement before the API layer:

- create case
- triage case
- make decision
- approve decision
- reject decision

## Next

1. Replace caller-controlled `approval_required` with policy evaluation in MakeDecision.
2. Add explicit rejection authority and actor identity.
3. Persist the policy/authority snapshot.
4. Add command-level idempotency, append-only audit, and transactional outbox behavior.
5. Expose API command boundaries only after these contracts are coherent.
