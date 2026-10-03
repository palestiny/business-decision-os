# CHECKPOINT-012

## Scope

Authority enforcement and policy authority at the decision approval boundary.

## Verified

- GitHub Actions run 82 for commit `dd9646bdaba527938664d47b3fb2fe7dffbec865` completed successfully.
- PostgreSQL 17 integration path passed across Python 3.12 and 3.13.
- PostgreSQL decision persistence verifies approval and rejection lifecycle state.
- Alembic migration round-trip and current-head verification passed.
- Alembic drift checking is part of CI.
- The earlier PostgreSQL FK ordering and SQLAlchemy session-cleanup failures are resolved.

## Added

- ApproveDecisionCommand carries the approving actor identity.
- ApproveDecisionHandler requires AuthorizationPort.
- RejectDecisionCommand carries the rejecting actor identity.
- RejectDecisionHandler requires AuthorizationPort.
- MakeDecision now obtains `approval_required` from PolicyEvaluatorPort instead of the caller.
- Evaluated policy identifiers are retained on Decision.
- Decision persistence stores the authority snapshot in the existing `authority_snapshot` field.
- Unit coverage verifies policy-driven approval and approval/rejection authority contracts.
- ADR-009 establishes policy evaluation as the authoritative source of approval requirements.

## Architectural rule

Approval has two independent boundaries:

1. **Policy evaluation** determines whether a decision requires approval and which policies caused that requirement.
2. **Authorization** determines whether the current actor may make, approve, or reject the decision.

A valid domain state alone is not sufficient to authorize protected commands.

## Decision

The caller must not be the source of truth for `approval_required`. The policy evaluator owns that decision, and the evaluated policy identifiers are retained in an authority snapshot for historical traceability.

See `docs/decisions/ADR-009-POLICY-AUTHORITY.md`.

## Verification boundary

The policy evaluator is currently only an application port; no production policy adapter is wired yet.

Create-case and triage command boundaries still need explicit actor identity and consistent authorization enforcement before the API layer.

Policy-evaluation failure semantics also need an executable application-level test before production API exposure; ADR-009 requires fail-closed behavior for protected approval policy evaluation.

## Next

1. Complete authority enforcement for create case and triage.
2. Define and test explicit fail-closed policy evaluation failure semantics.
3. Add command-level idempotency, append-only audit, and transactional outbox behavior.
4. Add integration coverage for authority snapshot round-trip.
5. Expose API command boundaries only after these contracts are coherent.
