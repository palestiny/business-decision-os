# CHECKPOINT-015

## Scope

Second-command reliability proof for `TriageCase`.

## Verified

- CI Run #153 (`36430357344`) completed successfully.
- Python 3.12 and 3.13 jobs passed.
- Alembic migration lifecycle and head checks passed.
- PostgreSQL integration tests passed.
- `TriageCaseReliabilityBoundary` was verified with real PostgreSQL persistence.
- Successful triage persisted the case transition, audit event, outbox message, and completed idempotency record atomically.
- Forced outbox failure rolled back the triage mutation and all reliability writes.
- Unit tests verify completed-request replay without a second mutation/commit.

## Decision

The reliability semantics are now proven for two materially different command shapes:

1. `CreateDecisionCase`: aggregate creation.
2. `TriageCase`: aggregate state transition.

This is sufficient evidence to proceed to a generic application-level reliability executor, provided the abstraction preserves command-specific request hashing, response serialization, audit action, outbox event, and authorization/policy behavior.

## Guardrails

- Genericization must remove duplication without moving reliability into the domain.
- The Unit of Work remains the sole transaction owner.
- Command handlers remain transaction-neutral.
- Do not hide authorization/policy semantics inside the generic executor.
- Keep command-specific domain behavior explicit.
- API exposure remains blocked until the API contract and post-commit publication semantics are separately verified.
- PR #2 remains unmerged pending explicit owner approval.
