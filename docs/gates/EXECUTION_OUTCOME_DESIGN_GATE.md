# EXECUTION OUTCOME DESIGN GATE

## Status

PASS — internal execution outcome and reconciliation semantics

## Locked

- Execution outcome is separate from Action start.
- UNKNOWN is distinct from FAILED.
- UNKNOWN cannot be retried blindly.
- UNKNOWN is resolved only through explicit reconciliation.
- Known execution success completes the Action.
- Known execution failure fails the Action.
- UNKNOWN keeps Action and Case execution unresolved.
- Known execution completion moves Case to OUTCOME_PENDING.
- Execution completion is not business Outcome verification.
- Provider payloads stay outside the domain.

## Not yet locked

- Provider-specific result schemas.
- Business Outcome calculation.
- Compensation/rollback.
- Automatic reconciliation strategy.

## Next implementation

Implement execution state transitions and the internal completion/reconciliation commands, then prove them with reliability and PostgreSQL tests.
