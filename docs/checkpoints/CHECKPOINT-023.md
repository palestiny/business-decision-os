# CHECKPOINT-023

## Scope

Start Analysis command boundary and first pre-decision lifecycle proof.

## Completed

- Added explicit `START_ANALYSIS` authorization permission.
- Added `StartAnalysisCommand` and transaction-neutral handler.
- Added `StartAnalysisReliabilityBoundary` using the shared reliability executor.
- Added HTTP command:
  - `POST /api/v1/decision-cases/{case_id}/analysis/start`
- API uses authenticated tenant/actor identity and requires `Idempotency-Key`.
- Added deterministic request hashing and replay serialization.
- Added transactional outbox topic `decision-case.analysis-started`.
- Added HTTP contract tests.
- Added PostgreSQL replay/integrity proof:
  - TRIAGED → ANALYZING
  - version increment
  - single audit event
  - single outbox message
  - idempotent replay
- Final CI for the resulting branch state passed on Python 3.12 and 3.13.

## Verification

PASS — CI runs #314 and #315 both succeeded.

## Architectural consistency

The command follows the existing lifecycle boundary:

HTTP → Application Command → Reliability Boundary → Domain → Persistence

The handler does not own transactions, and no generic status mutation endpoint was introduced.

## Important boundary

The remaining pre-decision lifecycle transitions `SubmitOptions` and `AwaitDecision` are not being implemented blindly yet. Their application semantics depend on what constitutes a valid persisted option set and the evidence/analysis completion contract. That is the next design decision to close before exposing those transitions.

## Next

Design and prove the Options stage, including option persistence/validation and the transition to `AWAITING_DECISION`.
