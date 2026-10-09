# ACTION DESIGN GATE

## Status
PASS — internal action lifecycle foundation

## Locked

- Action is separate from Decision.
- ActionExecution is separate from Action.
- Approval is required before Action becomes READY.
- UNKNOWN execution outcome is distinct from FAILED.
- Blind retry after UNKNOWN is prohibited.
- External execution uses a port/adapter.
- Action completion does not equal Outcome verification.
- Initial implementation has no real provider integration.

## Not yet locked

- Case-type-specific action payload schemas.
- Provider-specific integration contracts.
- Compensation/rollback semantics.
- Outcome calculation rules.

## Next implementation

Create Action domain + persistence, then implement CreateAction and StartAction with reliability, idempotency, audit, outbox, and PostgreSQL replay proof.
