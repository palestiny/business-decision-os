# CHECKPOINT-012

## Scope

Authority enforcement at the decision approval command boundary.

## Verified

- GitHub Actions run 53 for commit b33c690 completed successfully.
- PostgreSQL 17 integration path passed across Python 3.12 and 3.13.
- Alembic migration round-trip and current-head verification passed.
- Alembic drift checking is part of CI.
- The earlier PostgreSQL FK ordering and SQLAlchemy session-cleanup failures are resolved.

## Added

- ApproveDecisionCommand now carries the approving actor identity.
- ApproveDecisionHandler requires AuthorizationPort.
- Approval authorization is checked with Permission.APPROVE_DECISION before mutating the Decision.
- Unit coverage verifies the authority call contract and preserves tenant/case scoping.

## Architectural rule

Approval is both a domain transition and an authority-controlled application command. A valid domain state alone is not sufficient to authorize approval.

## Verification boundary

The authority integration currently uses the application port contract; a production authorization adapter/policy implementation is not yet wired into composition.

## Next

1. Verify PostgreSQL persistence for approval/rejection state transitions.
2. Complete policy evaluation semantics for approval requirements and protected actions.
3. Add idempotency/audit/outbox behavior around command execution.
4. Expose API command boundaries only after these application contracts are coherent.
