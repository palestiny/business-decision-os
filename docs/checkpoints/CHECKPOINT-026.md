# CHECKPOINT-026

## Scope

Establish and verify the Action / ActionExecution boundary before external execution work.

## Decisions

- Action is business intent authorized by a Decision.
- ActionExecution is a concrete execution attempt.
- An Action may have multiple execution attempts.
- UNKNOWN is a first-class execution result and is not treated as FAILED.
- Action completion is not Outcome verification.
- No provider integration is introduced in this stage.
- CreateAction requires an APPROVED case and APPROVED decision, then creates the Action in READY for the initial internal slice.
- StartAction creates the execution attempt and atomically moves the Action and Case into EXECUTING.

## Added

- `docs/decisions/ADR-012-ACTION-EXECUTION-BOUNDARY.md`
- `docs/gates/ACTION_DESIGN_GATE.md`
- Action domain primitives.
- Action and ActionExecution repository ports.
- PostgreSQL persistence models and migration `0004_action_execution`.
- CreateAction / StartAction application handlers and reliability boundaries.
- HTTP endpoints for Action creation and execution start.
- Action command unit tests.

## Verification

**PASS**

GitHub Actions CI run #414 passed on both Python 3.12 and 3.13.

Verified by CI:
- Alembic upgrade to head.
- Alembic downgrade to base.
- Alembic upgrade from base.
- `alembic current --check-heads`.
- `alembic check`.
- Full pytest suite.

The tested implementation includes the action persistence migration and the action command invariants.

## Safety properties verified

- Action creation does not execute the action.
- Action creation requires both case and decision approval.
- StartAction creates attempt 1.
- UNKNOWN execution blocks blind retry.
- Action and Case optimistic concurrency versions are captured explicitly.
- Reliability boundary provides idempotency, audit, outbox, and transaction ownership.
- No external provider is invoked.

## Next

Proceed to execution outcome semantics and reconciliation design before adding any real provider integration.
