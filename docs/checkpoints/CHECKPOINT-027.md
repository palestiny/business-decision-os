# CHECKPOINT-027

## Scope

Execution outcome and UNKNOWN reconciliation foundation.

## Status

PASS

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

CI #478 passed on Python 3.12 and 3.13 after the fixture corrections.

Previous CI run #468 exposed four test issues:
1. StartAction test expected RUNNING while implementation still persisted REQUESTED.
2. Outcome test used APPROVED Case instead of EXECUTING Case.
3. Two unit fakes had stale execution-save signatures.

The fixes remain at the test boundary. No architectural workaround was used.

## Next

Checkpoint verified. Next: Business Outcome + Verification design gate.
