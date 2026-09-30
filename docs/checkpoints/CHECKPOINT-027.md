# CHECKPOINT-027

## Scope

Execution outcome and UNKNOWN reconciliation foundation.

## Status

NOT YET PROVEN

## Design

ADR-013 and the execution outcome design gate establish:

- REQUESTED → RUNNING
- RUNNING → SUCCEEDED | FAILED | UNKNOWN
- UNKNOWN → SUCCEEDED | FAILED only through explicit reconciliation
- UNKNOWN blocks blind retry
- known terminal execution completes/fails the Action
- known terminal execution moves the Case to OUTCOME_PENDING
- UNKNOWN leaves the Case and Action execution unresolved
- execution completion is not business Outcome verification

## Implementation

Added:

- execution domain transitions
- execution persistence compare-and-swap by expected status
- completion command
- UNKNOWN command
- reconciliation command
- reliability/idempotency/audit/outbox boundaries
- HTTP endpoints
- unit coverage

## Verification

CI run #472 is currently in progress on Python 3.12 and 3.13.

Previous CI run #468 exposed four test issues:
1. StartAction test expected RUNNING while implementation still persisted REQUESTED.
2. Outcome test used APPROVED Case instead of EXECUTING Case.
3. Two unit fakes had stale execution-save signatures.

Those are being corrected at the source/test boundary. No architectural workaround was used.

## Next

Verify CI #472. If green, mark CHECKPOINT-027 PASS. If not, inspect the actual failing job and fix root cause before proceeding.
