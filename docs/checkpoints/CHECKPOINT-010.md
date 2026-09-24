# CHECKPOINT-010

## Scope

Persistence verification contracts and CI hardening.

## Added

- Persistence integration-contract tests validate the complete v0.1 table set can be materialized by SQLAlchemy metadata.
- Tenant scoping and optimistic version columns are explicitly asserted.
- Tenant + operation + idempotency key uniqueness is explicitly asserted.
- GitHub Actions now provides the runtime path for Python test verification on supported Python versions.

## Verification boundary

The repository now has automated CI coverage, but the local assistant environment still has no verified PostgreSQL runtime. Therefore PostgreSQL migration execution remains **NOT VERIFIED HERE**.

## Reliability rule

The repository's current concurrency implementation uses an explicit version predicate on updates. SQLAlchemy also documents version-counter support for stale/concurrent update detection; we will keep the domain/application version as the authoritative contract and use ORM/database facilities only as infrastructure enforcement.

## Next

Add real PostgreSQL service coverage to CI, run Alembic upgrade/downgrade from an empty database, and test repository round-trips plus concurrency conflicts.
