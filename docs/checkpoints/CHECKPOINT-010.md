# CHECKPOINT-010

## Scope

Persistence verification contracts and CI hardening.

## Added

- Persistence integration-contract tests validate the complete v0.1 table set can be materialized by SQLAlchemy metadata.
- Tenant scoping and optimistic version columns are explicitly asserted.
- Tenant + operation + idempotency key uniqueness is explicitly asserted.
- GitHub Actions now provides PostgreSQL 17 service coverage for Python 3.12 and 3.13.
- CI now exercises Alembic upgrade, downgrade to base, upgrade again, and head-state verification.
- PostgreSQL integration tests cover repository round-trip, tenant isolation, optimistic concurrency conflict, and transaction rollback.
- Alembic now honors `SQLALCHEMY_DATABASE_URL` for both offline and online migration execution.
- Decision persistence save is tenant-scoped to prevent cross-tenant mutation by identifier.

## Verification boundary

The first CI run for the persistence integration failed before migrations because `alembic/env.py` called `fileConfig()` against the deliberately minimal `alembic.ini`, which has no `[formatters]` section. The root cause was fixed in commit `81bea0e6750a42c5c22c86378172a464f73ae54d` by removing the invalid logging bootstrap. A new workflow run has not yet been observed, so PostgreSQL runtime verification remains **NOT VERIFIED YET**.

## Reliability rule

The repository's current concurrency implementation uses an explicit version predicate on updates. SQLAlchemy also documents version-counter support for stale/concurrent update detection; we will keep the domain/application version as the authoritative contract and use ORM/database facilities only as infrastructure enforcement.

## Next

Observe the CI run for the persistence branch. If green, proceed to complete Decision persistence/application wiring and then expose the first API command boundary. If CI fails, fix the root cause before advancing.
