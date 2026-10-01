# CHECKPOINT-030

## Scope

First-slice hardening: enforce the approved modular-monolith dependency direction with automated architecture tests.

## Status

IMPLEMENTED — CI verification pending.

## Implemented

- Added architecture tests under `tests/architecture/`.
- Domain modules are guarded against imports from application, infrastructure, FastAPI, SQLAlchemy, and psycopg.
- Application core is guarded against infrastructure imports.
- Architecture test suite verifies the expected domain/application/infrastructure package boundaries exist.

## Why

The first vertical slice is now end-to-end at the behavior level. The next reliability risk is architectural drift: domain or application code accidentally taking dependencies on infrastructure concerns. These tests turn the approved dependency direction into an executable guardrail.

## Verification

Before this checkpoint, branch head CI run #609 passed on:

- Python 3.12
- Python 3.13
- PostgreSQL 17
- Alembic upgrade/downgrade/upgrade
- Alembic head check
- Alembic schema drift check
- pytest

A new CI run is required because this checkpoint adds new tests.

## Remaining Foundation Gap

- Clock and ID abstractions remain intentionally open.
- Domain events remain deferred; transactional outbox is already in place.

## Next

Verify CHECKPOINT-030 in CI. If green, move to first-slice operational hardening and decide whether Clock/ID abstractions are justified before adding further domain complexity.
