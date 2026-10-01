# CHECKPOINT-004

## Scope

Application Architecture and persistence strategy.

## Completed

- Command/query separation defined.
- Explicit command handlers defined.
- Unit of Work defined.
- Transaction-per-command rule defined.
- Authorization pipeline defined.
- Permission, policy, decision authority, and action authority separated.
- Idempotency defined.
- Optimistic concurrency defined.
- Transactional Outbox selected.
- External execution/reconciliation flow defined.
- Unified error contract defined.
- Tenant isolation defined.
- PostgreSQL selected.
- Migration-first strategy selected.

## Current status

Architecture is ready for implementation of the thin vertical slice.

## Not yet implemented

- Domain code
- Application handlers
- Database migrations
- API endpoints
- Tests
- External integrations
- AI adapters

## Next action

TDD RED for DecisionCase lifecycle and MakeDecision invariants.
